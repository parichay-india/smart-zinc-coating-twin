# Smart Zinc Coating — Physics-Backed Digital Twin (HDGL · CRM-III)

A game-like, 3-D Streamlit digital twin of the **air-knife coating section** of a continuous
hot-dip galvanizing line. It runs the **PG-HGBT** soft sensor — a *physics-guided* model that
infers per-side zinc coating weight from live process signals — with **calibrated conformal
uncertainty**, a **closed-loop minimum-zinc set-point recommendation**, a full **16-model
comparison**, a **physics explainer**, and the **quantified before/after zinc savings**.

> Built after the line's in-line X-ray coating gauge became unavailable, forcing open-loop
> operation and systematic over-coating. The twin restores on-target control entirely in software.

## What's inside

| File | Purpose |
|------|---------|
| `app.py` | Streamlit app (6 tabs: Live Twin, Model Comparison, Physics Explainer, Process & Savings, How it Works, About) |
| `twin3d.py` | Self-contained three.js 3-D scene (strip, zinc pot, air knives, jets, steam, sparks; orbit/zoom, preset views) |
| `physics.py` | Calibrated air-knife wiping power-law (physics core + min-zinc pressure solver) |
| `model_utils.py` | Loads the model bundle, builds the physics feature, predicts with the conformal band |
| `train_models.py` | Regenerates the model bundle + benchmark from `data/` |
| `models/pg_hgbt_frontcoating.pkl` | Pre-trained PG-HGBT bundle (ships with the repo) |
| `models/benchmark_metrics.json` | The 16-model comparison table |
| `kpis.json` | Validated before/after operational KPIs |

## The model

A calibrated **jet-wiping power-law** (coating rises with line speed and stand-off, falls with
air-knife pressure) explains ≈0.76 of coating variance on its own and is injected as a feature.
**PG-HGBT** then learns the residual. In a 16-learner benchmark (classical, kernel, Gaussian
process, deep MLP, XGBoost, LightGBM, CatBoost, random/extra-trees), the **physics-guided
ensemble attains the highest R² (0.904) and the lowest RMSE**, ahead of the strongest
data-driven baseline in 99.9 % of paired bootstrap resamples — and is the only top model that is
physically consistent, interpretable and uncertainty-calibrated. A single physics-guided HGBT
runs sub-millisecond at the edge.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Retrain (optional)

```bash
pip install -r requirements-train.txt
# put PeriodA.csv / PeriodB.csv in data/
python train_models.py
```

> The shipped `.pkl` was trained with a recent scikit-learn. If you see a version warning,
> simply re-run `train_models.py` (or the Colab notebook) to regenerate it against your installed
> version — it is harmless otherwise.

## Deploy

The repository is ready for **Streamlit Community Cloud** (point it at `app.py`) or Docker
(`docker build -t zinc-twin . && docker run -p 8501:8501 zinc-twin`). See the deployment guide.

---
*SAIL · Bokaro Steel Plant · Cold Rolling Mill-III · HDGL. Engineering demonstration; the 3-D
scene is an illustrative emulator. Subject of a filed Indian patent.*
