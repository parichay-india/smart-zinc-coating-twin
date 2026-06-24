"""Regenerate the PG-HGBT model bundle and the model-comparison benchmark from plant data.

Usage:  python train_models.py            (expects data/PeriodA.csv [, data/PeriodB.csv])

Pipeline (identical to the Colab notebook):
  1. load running-line records
  2. calibrate the air-knife wiping power-law (physics feature, fit on train only)
  3. train a 16-learner zoo (classical, kernel, probabilistic, deep, modern GBMs, bagging)
  4. build PG-HGBT: a single physics-guided HGBT (deployable) + a physics-guided stacked ensemble
  5. split-conformal uncertainty band
  6. export models/pg_hgbt_frontcoating.pkl  and  models/benchmark_metrics.json
"""
import os, glob, json, time, warnings, joblib
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split, KFold
from sklearn.base import clone
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression, Ridge, RidgeCV
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TARGET = "frontCoating"
SAMPLE, SEED = 80_000, 7
RAW = ["processSpeed","width","thickness","frontPressure","rearPressure","frontHP","rearHP",
       "vPos","frontTilt","rearTilt","potTemp","snoutTemp"]
PHYS_VARS = ["processSpeed","frontPressure","frontHP","width"]


def main():
    files = sorted(glob.glob(os.path.join(DATA, "*.csv")))
    assert files, f"Put PeriodA.csv / PeriodB.csv in {DATA}"
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    run = df[df.lineState == "RUNNING"].dropna(subset=RAW + [TARGET]).reset_index(drop=True)
    print(f"running-line records: {len(run):,}")
    samp = run.sample(min(SAMPLE, len(run)), random_state=SEED).reset_index(drop=True)
    itr, ite = train_test_split(np.arange(len(samp)), test_size=0.30, random_state=SEED)
    ytr, yte = samp[TARGET].values[itr], samp[TARGET].values[ite]

    logm = lambda d: np.column_stack([np.log(np.clip(d[c].values, 1e-3, None)) for c in PHYS_VARS])
    theta, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(itr)), logm(samp.iloc[itr])]),
                                np.log(np.clip(ytr, 1e-3, None)), rcond=None)
    samp["m_phys"] = np.exp(np.column_stack([np.ones(len(samp)), logm(samp)]) @ theta)
    FEAT_P = RAW + ["m_phys"]
    X, Xp = samp[RAW].values.astype(float), samp[FEAT_P].values.astype(float)
    Xtr, Xte, Xptr, Xpte = X[itr], X[ite], Xp[itr], Xp[ite]
    sc = StandardScaler().fit(Xtr); Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
    phys_te = np.exp(np.column_stack([np.ones(len(ite)), logm(samp.iloc[ite])]) @ theta)
    print("calibrated exponents:", np.round(theta, 4))

    import xgboost as xgb, lightgbm as lgb
    from catboost import CatBoostRegressor
    rows, preds = [], {}
    def rec(n, fam, p, note=""):
        rows.append(dict(Model=n, Family=fam, R2=round(float(r2_score(yte, p)), 4),
                         MAE=round(float(mean_absolute_error(yte, p)), 3),
                         RMSE=round(float(np.sqrt(mean_squared_error(yte, p))), 3), Note=note))
        preds[n] = p; print(f"  {n:24s} R2={rows[-1]['R2']:.4f}")
    rec("Physics-only (power law)", "Physics", phys_te, "calibrated wiping law")
    sub = np.random.default_rng(0).choice(len(Xtr), min(6000, len(Xtr)), replace=False)
    def fit(n, fam, m, Xt, Xv, note=""): m.fit(Xt, ytr); rec(n, fam, m.predict(Xv), note)
    fit("Linear", "Classical", LinearRegression(), Xtr, Xte)
    fit("Ridge", "Classical", Ridge(1.0), Xtr, Xte)
    fit("k-NN", "Classical", KNeighborsRegressor(15), Xtr_s, Xte_s)
    fit("MLP", "Deep learning", MLPRegressor((128, 64), max_iter=200, early_stopping=True, random_state=0), Xtr_s, Xte_s)
    fit("HistGB", "Boosting", HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, random_state=0), Xtr, Xte)
    fit("XGBoost", "Boosting", xgb.XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=7, subsample=0.9, colsample_bytree=0.9, n_jobs=-1, random_state=0, tree_method="hist"), Xtr, Xte)
    fit("LightGBM", "Boosting", lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63, n_jobs=-1, random_state=0, verbose=-1), Xtr, Xte)
    fit("CatBoost", "Boosting", CatBoostRegressor(iterations=600, learning_rate=0.05, depth=8, verbose=0, random_state=0), Xtr, Xte)
    fit("RandomForest", "Ensemble", RandomForestRegressor(300, n_jobs=-1, random_state=0), Xtr, Xte)
    fit("ExtraTrees", "Ensemble", ExtraTreesRegressor(300, n_jobs=-1, random_state=0), Xtr, Xte)
    rec("SVR", "Kernel", make_pipeline(StandardScaler(), SVR(C=20, gamma="scale")).fit(Xtr[sub], ytr[sub]).predict(Xte), "subsample")
    try:
        rec("GaussianProcess", "Probabilistic", make_pipeline(StandardScaler(), GaussianProcessRegressor(kernel=RBF()+WhiteKernel(), normalize_y=True)).fit(Xtr[sub][:2000], ytr[sub][:2000]).predict(Xte), "subsample")
    except Exception as e: print("  GP skipped:", e)
    rec("Blend (RF+HGB)", "Ensemble", (preds["RandomForest"] + preds["HistGB"]) / 2, "average")

    # deployable single physics-guided HGBT
    single = HistGradientBoostingRegressor(max_iter=1000, learning_rate=0.05, max_leaf_nodes=255,
              min_samples_leaf=20, early_stopping=True, validation_fraction=0.1, n_iter_no_change=40, random_state=0).fit(Xptr, ytr)
    rec("PG-HGBT single", "Physics-guided", single.predict(Xpte), "physics feature + boosting (edge)")
    q90 = float(np.quantile(np.abs(yte - single.predict(Xpte)), 0.9))

    # physics-guided stacked ensemble = PG-HGBT (ours)
    bases = {"ET": ExtraTreesRegressor(300, n_jobs=-1, random_state=0),
             "HGB": HistGradientBoostingRegressor(max_iter=1000, learning_rate=0.05, max_leaf_nodes=255, min_samples_leaf=20, random_state=0),
             "XGB": xgb.XGBRegressor(n_estimators=600, learning_rate=0.05, max_depth=8, subsample=0.9, colsample_bytree=0.9, n_jobs=-1, random_state=0, tree_method="hist"),
             "LGB": lgb.LGBMRegressor(n_estimators=800, learning_rate=0.05, num_leaves=127, n_jobs=-1, random_state=0, verbose=-1)}
    kf = KFold(5, shuffle=True, random_state=0)
    oof, test = np.zeros((len(itr), len(bases))), np.zeros((len(ite), len(bases)))
    for j, (nm, mdl) in enumerate(bases.items()):
        of = np.zeros(len(itr))
        for trk, vak in kf.split(Xptr):
            of[vak] = clone(mdl).fit(Xptr[trk], ytr[trk]).predict(Xptr[vak])
        oof[:, j] = of; mdl.fit(Xptr, ytr); test[:, j] = mdl.predict(Xpte)
    mi = FEAT_P.index("m_phys")
    meta = RidgeCV(alphas=[0.01, 0.1, 1, 10]).fit(np.column_stack([oof, Xptr[:, mi]]), ytr)
    rec("PG-HGBT (ours)", "Physics-guided ensemble", meta.predict(np.column_stack([test, Xpte[:, mi]])), "physics-fed stack + conformal")

    rows = sorted(rows, key=lambda r: -r["R2"])
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    joblib.dump(dict(model=single, features=FEAT_P, target=TARGET, conformal_q90=round(q90, 4),
                     phys_coef=theta.tolist(), phys_vars=PHYS_VARS,
                     phys_formula="ln(m_phys)=c0+c1*ln(processSpeed)+c2*ln(frontPressure)+c3*ln(frontHP)+c4*ln(width)",
                     benchmark=rows, trained_at=time.strftime("%Y-%m-%d %H:%M")),
                os.path.join(HERE, "models", "pg_hgbt_frontcoating.pkl"), compress=3)  # compress -> ~12 MB, under GitHub's 25 MB web limit
    json.dump(rows, open(os.path.join(HERE, "models", "benchmark_metrics.json"), "w"), indent=1)
    print(f"\nBEST: {rows[0]['Model']}  R2={rows[0]['R2']}  | conformal q90={q90:.2f} g/m²")
    print("exported models/pg_hgbt_frontcoating.pkl + models/benchmark_metrics.json")


if __name__ == "__main__":
    main()
