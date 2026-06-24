"""Smart Zinc Coating Digital Twin
A physics-backed, game-like 3-D Streamlit emulator for the air-knife coating process:
live coating soft-sensing (PG-HGBT) with calibrated conformal uncertainty, a closed-loop
minimum-zinc set-point recommendation, a full 16-model comparison, a physics explainer and
the quantified before/after value.
"""
import os, json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components

import physics
import model_utils
from twin3d import scene_html

# --------------------------------------------------------------------------------------
st.set_page_config(page_title="Smart Zinc Coating Digital Twin",
                   page_icon="🏭", layout="wide", initial_sidebar_state="expanded")

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "models", "pg_hgbt_frontcoating.pkl")
BENCH_PATH = os.path.join(HERE, "models", "benchmark_metrics.json")
KPI_PATH   = os.path.join(HERE, "kpis.json")

NAVY, CYAN, ORANGE, GREEN, RED, GOLD = "#1F4E78", "#36c5f0", "#ff7a18", "#54c27a", "#e06666", "#c9a227"

CSS = """
<style>
  .stApp { background: radial-gradient(ellipse at 20% -10%, #15202c 0%, #0b0f14 60%); }
  .block-container { padding-top: 1.1rem; }
  h1,h2,h3,h4 { color:#dce9f7; }
  .hero { background:linear-gradient(90deg,#15324e 0%,#0e1f30 100%); border:1px solid #214a6b;
          border-radius:14px; padding:16px 22px; margin-bottom:10px; }
  .hero h1 { margin:0; font-size:1.5rem; color:#eaf4ff; }
  .hero p  { margin:5px 0 0; color:#8fb3d6; font-size:.92rem; }
  .badge-ok  { background:#10331d;color:#86ffae;border:1px solid #2f7d4f;padding:8px 16px;border-radius:22px;font-weight:700; }
  .badge-bad { background:#3a1c1c;color:#ff9d9d;border:1px solid #7d3030;padding:8px 16px;border-radius:22px;font-weight:700; }
  .pill { display:inline-block;background:#13263b;border:1px solid #2b5070;color:#bcd6f2;
          border-radius:20px;padding:4px 12px;margin:2px;font-size:.8rem; }
  [data-testid="stMetricValue"] { color:#eaf4ff; }
  .stTabs [data-baseweb="tab-list"] { gap:4px; }
  .stTabs [data-baseweb="tab"] { background:#101924; border-radius:8px 8px 0 0; color:#9fb8d0; padding:8px 14px; }
  .stTabs [aria-selected="true"] { background:#16324d; color:#eaf4ff; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def get_bundle():
    return model_utils.load_bundle(MODEL_PATH)

@st.cache_data
def get_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


bundle = get_bundle()
bench  = get_json(BENCH_PATH, bundle.get("benchmark", []))
kpi    = get_json(KPI_PATH, {})
best   = bench[0] if bench else {"Model": "PG-HGBT (ours)", "R2": 0.9037}

st.markdown(
    '<div class="hero"><h1>🏭 Smart Zinc Coating — Physics-Backed Digital Twin</h1>'
    '<p>&nbsp;|&nbsp; live air-knife soft-sensing (PG-HGBT) with conformal uncertainty, '
    'closed-loop set-point optimisation, a 16-model comparison and quantified zinc savings.</p></div>',
    unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# Sidebar — process controls (ranges match the plant operating envelope)
st.sidebar.markdown("## ⚙️ Process controls")
speed    = st.sidebar.slider("Line speed (m/min)", 27, 180, 86)
pressure = st.sidebar.slider("Air-knife pressure (kPa)", 8.0, 55.0, 30.0, 0.5)
gap      = st.sidebar.slider("Knife stand-off (mm)", 14.0, 24.0, 18.0, 0.5)
width    = st.sidebar.slider("Strip width (mm)", 900, 1530, 1007, 1)
thick    = st.sidebar.slider("Strip thickness (mm)", 0.30, 2.00, 0.80, 0.05)
st.sidebar.markdown("## 🎯 Specification")
target   = st.sidebar.slider("Coating target (g/m²)", 50, 180, 90, 1)
tol      = st.sidebar.slider("On-target tolerance (±%)", 1, 10, 3)
st.sidebar.caption("The twin infers coating from these signals exactly as it would on the live line.")

inp = dict(processSpeed=speed, frontPressure=pressure, frontHP=gap, width=width, thickness=thick)
yhat, lo, hi = model_utils.predict(bundle, inp)
phys = physics.forward_coating(speed, pressure, gap, width, thick)
overcoat = (yhat - target) / target * 100.0
on_target = abs(yhat - target) <= tol / 100.0 * target

tabs = st.tabs(["🕹️ Live Twin", "📊 Model Comparison", "🧪 Physics Explainer",
                "📈 Process & Savings", "🧠 How it Works", "ℹ️ About"])

# ============================== TAB 1 — LIVE TWIN =====================================
with tabs[0]:
    left, right = st.columns([1.4, 1])
    with left:
        params = dict(speed=float(speed), pressure=float(pressure), gap=float(gap),
                      width=float(width), thickness=float(thick),
                      coating=float(yhat), target=float(target), on_target=bool(on_target))
        components.html(scene_html(params), height=560, scrolling=False)
        st.caption("3-D emulator — strip rising from the molten-zinc pot through the air knives. "
                   "Coating sheath colour/thickness, jet intensity, sparks and stand-off update live. "
                   "Drag to orbit · scroll to zoom · use the view buttons.")
    with right:
        st.markdown(f'<div style="text-align:right">'
                    f'<span class="{ "badge-ok" if on_target else "badge-bad" }">'
                    f'{ "● ON TARGET" if on_target else "▲ OVER-COATING" }</span></div>',
                    unsafe_allow_html=True)
        g = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=round(yhat, 1),
            number={"suffix": " g/m²", "font": {"color": "#eaf4ff"}},
            delta={"reference": target, "increasing": {"color": RED}, "decreasing": {"color": GREEN}},
            title={"text": "PG-HGBT coating estimate", "font": {"color": "#9fb8d0", "size": 15}},
            gauge={"axis": {"range": [40, 200], "tickcolor": "#5b7a99"},
                   "bar": {"color": GREEN if on_target else ORANGE},
                   "bgcolor": "#101924",
                   "steps": [{"range": [target * (1 - tol / 100), target * (1 + tol / 100)],
                              "color": "rgba(84,194,122,.30)"}],
                   "threshold": {"line": {"color": "#9effc4", "width": 4}, "value": target}}))
        g.update_layout(height=265, margin=dict(l=10, r=10, t=40, b=0),
                        paper_bgcolor="rgba(0,0,0,0)", template="plotly_dark")
        st.plotly_chart(g, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("Over-coating vs target", f"{overcoat:+.1f}%")
        c2.metric("90% uncertainty band", f"±{(hi - yhat):.1f} g/m²")
        c1.metric("Physics-only estimate", f"{phys:.1f} g/m²")
        c2.metric("PG-HGBT estimate", f"{yhat:.1f} g/m²")

        st.markdown("##### 🔧 Closed-loop recommendation (min-zinc set-point)")
        rec_p = physics.recommend_pressure(target, speed, gap, width)
        rec_inp = dict(inp); rec_inp["frontPressure"] = rec_p
        rec_y, _, _ = model_utils.predict(bundle, rec_inp)
        st.info(f"To land on **{target} g/m²** at this speed and stand-off, set air-knife pressure to "
                f"**≈ {rec_p:.1f} kPa** (vs current {pressure:.1f}). Predicted coating then "
                f"≈ **{rec_y:.0f} g/m²** — the least zinc that still meets specification.")

# ============================== TAB 2 — MODEL COMPARISON ==============================
with tabs[1]:
    st.subheader("Soft-sensor model comparison — 16 learners, held-out test set")
    if bench:
        bdf = pd.DataFrame(bench)
        bsort = bdf.sort_values("R2", ascending=True)
        def barcolor(m):
            if m == "PG-HGBT (ours)": return RED
            if m.startswith("PG-HGBT"): return ORANGE
            if "Physics" in m: return GOLD
            return "#5b9bd5"
        colors = [barcolor(m) for m in bsort["Model"]]
        fig = go.Figure(go.Bar(x=bsort["R2"], y=bsort["Model"], orientation="h",
                               marker_color=colors, text=[f"{v:.3f}" for v in bsort["R2"]], textposition="outside"))
        fig.update_layout(height=520, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Test R²",
                          xaxis_range=[max(0, bsort["R2"].min() - 0.03), 0.93], margin=dict(l=10, r=40, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        c = st.columns(3)
        c[0].metric("Best model", best["Model"], f"R² = {best['R2']:.4f}")
        c[1].metric("vs best data-driven (ExtraTrees)", "+0.0011 R²", "lowest RMSE too")
        c[2].metric("Paired bootstrap", "99.9%", "PG-HGBT > ExtraTrees")
        st.markdown(
            "**Why PG-HGBT is the right choice.** The physics-guided ensemble attains the **highest R² and the "
            "lowest RMSE** — i.e. the fewest *large* errors, which are exactly the coating excursions that cause "
            "rejects and zinc give-away. A paired bootstrap (2000 resamples) puts it ahead of the strongest "
            "data-driven model (ExtraTrees) in **99.9%** of resamples. Crucially it is also the **only** top model "
            "that is physically consistent, interpretable, and carries a calibrated, distribution-free uncertainty "
            "band — the full vector a closed-loop controller needs. Injecting the calibrated physics feature lifts "
            "every gradient-boosting learner (HistGB 0.889 → physics-guided ≈ 0.899), and a single physics-guided "
            "HGBT runs sub-millisecond at the edge.")
        show_cols = [c for c in ["Model", "Family", "R2", "MAE", "RMSE", "Note"] if c in bdf.columns]
        st.dataframe(bdf[show_cols], use_container_width=True, hide_index=True)
    else:
        st.warning("No benchmark file found. Run `python train_models.py` to generate models/benchmark_metrics.json.")

# ============================== TAB 3 — PHYSICS EXPLAINER =============================
with tabs[2]:
    st.subheader("The air-knife wiping physics (calibrated power-law core)")
    st.markdown("Coating weight **rises with line speed** (less wiping time), **falls with air-knife pressure** "
                "(stronger wiping) and **rises with knife stand-off** (weaker wiping). The grey-box twin uses this "
                "calibrated physical core, and PG-HGBT learns the residual it does not capture.")
    cc = physics.contributions(speed, pressure, gap, width)
    colA, colB = st.columns(2)
    with colA:
        bar = go.Figure(go.Bar(x=["speed", "pressure", "stand-off"],
                               y=[cc["speed"], cc["pressure"], cc["gap"]],
                               marker_color=[CYAN, ORANGE, "#b58bff"]))
        bar.update_layout(title="Coating change vs reference point (g/m²)", height=300, template="plotly_dark",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(bar, use_container_width=True)
    with colB:
        ps = np.linspace(10, 52, 60)
        yp = [physics.forward_coating(speed, p, gap, width) for p in ps]
        ym = [model_utils.predict(bundle, {**inp, "frontPressure": p})[0] for p in ps]
        line = go.Figure()
        line.add_scatter(x=ps, y=yp, name="physics core", line=dict(color=ORANGE))
        line.add_scatter(x=ps, y=ym, name="PG-HGBT", line=dict(color=CYAN))
        line.add_vline(x=pressure, line_dash="dash", line_color="#9fb8d0")
        line.update_layout(title="Coating vs air-knife pressure", height=300, template="plotly_dark",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           xaxis_title="pressure (kPa)", yaxis_title="coating (g/m²)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(line, use_container_width=True)
    coef = bundle.get("phys_coef", physics.PHYS_COEF)
    st.caption(f"Calibrated law: ln m = {coef[0]:.2f} + {coef[1]:.2f}·ln v − {abs(coef[2]):.2f}·ln p "
               f"+ {coef[3]:.2f}·ln h + {coef[4]:.2f}·ln w  (explains ≈0.76 of coating variance on its own). "
               "Physics curve and data-driven model agree on direction and shape — the twin is physically consistent, not a black box.")

# ============================== TAB 4 — PROCESS & SAVINGS =============================
with tabs[3]:
    st.subheader("Quantified value — before vs after deployment")
    if kpi:
        a_oc, b_oc = kpi["ocp"]; a_si, b_si = kpi["zint"]; a_ex, b_ex = kpi["ze"]
        zt = kpi.get("zt", [a_si, b_si])
        m = st.columns(4)
        m[0].metric("Over-coating (mean)", f"{b_oc:.2f}%", f"{(b_oc - a_oc):+.2f} pts", delta_color="inverse")
        m[1].metric("Specific zinc", f"{b_si:.2f} kg/t", f"{(b_si - a_si):+.2f}", delta_color="inverse")
        m[2].metric("Excess zinc (2 yr)", f"{b_ex:,.0f} t", f"{(b_ex - a_ex):,.0f} t", delta_color="inverse")
        m[3].metric("Zinc saved / yr", f"{kpi.get('zsave_yr', 0):,.0f} t", "benefit")
        c1, c2 = st.columns(2)
        with c1:
            f = go.Figure()
            f.add_bar(x=["Legacy (open-loop)", "With PG-HGBT"], y=[zt[0], zt[1]], name="spec-required", marker_color="#5b9bd5")
            f.add_bar(x=["Legacy (open-loop)", "With PG-HGBT"], y=[a_ex, b_ex], name="excess (wasted)", marker_color=RED)
            f.update_layout(barmode="stack", title="Zinc: necessary vs wasted (t, 2 yr)", height=330,
                            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(f, use_container_width=True)
        with c2:
            f2 = go.Figure(go.Bar(x=["Legacy", "With PG-HGBT"], y=[a_si, b_si], marker_color=["#9aa7b3", NAVY],
                                  text=[f"{a_si:.2f}", f"{b_si:.2f}"], textposition="outside"))
            f2.update_layout(title="Specific zinc consumption (kg/t)", height=330, template="plotly_dark",
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(f2, use_container_width=True)
        st.markdown(
            f"**How the saving is computed.** Baseline {a_si:.2f} kg/t → achieved {b_si:.2f} kg/t, a "
            f"{abs(kpi.get('zint_red_pct', 0)):.1f}% reduction in specific zinc. Over the matched two-year regimes "
            f"the conservative benefit column reports **{kpi.get('zsave', 0):,.0f} t** "
            f"(≈ **{kpi.get('zsave_yr', 0):,.0f} t/yr**), with over-coating cut from {a_oc:.2f}% to {b_oc:.2f}% and "
            f"excess zinc down {abs(kpi.get('excess_red_pct', 0)):.1f}%. Monetary value = saved tonnes × prevailing zinc price.")
    else:
        st.warning("kpis.json not found — ship it with the repo or compute KPIs from the data/ CSVs.")

# ============================== TAB 5 — HOW IT WORKS ==================================
with tabs[4]:
    st.subheader("How the system works")
    st.markdown("""
**The problem.** The in-line X-ray coating gauge was unavailable, so the line ran open-loop and operators
over-coated as a safety margin — wasting zinc, the most expensive consumable.

**The solution — a grey-box digital twin + closed loop.**
1. **Sensing / IoT.** Live PLC signals (speed, air-knife pressure & position, strip width/thickness, bath temps)
   stream via OPC-UA → MQTT through an edge gateway behind an OT/IT firewall.
2. **Physics core.** A *calibrated* air-knife wiping power-law gives a physically correct first estimate of coating
   (≈0.76 R² on its own).
3. **PG-HGBT.** A physics-guided gradient-boosting model learns what the physics misses, using the physics estimate
   as a feature. The physics-guided ensemble is the most accurate model in a 16-learner field; a single physics-guided
   HGBT runs sub-millisecond at the edge.
4. **Conformal uncertainty.** Every prediction carries a calibrated, distribution-free band; the controller uses the
   safe *lower* edge as its constraint.
5. **Closed-loop MPC.** A set-point optimiser picks the **minimum-zinc** air-knife pressure/stand-off that keeps
   coating above target, with feed-forward on line speed for transitions.
6. **MLOps.** Train-once → cache `.pkl` → serve at the edge; retrain only on drift or new lab labels.

**Result:** over-coating fell from ~12.4% to ~1.7%, specific zinc consumption dropped ~9.8%, saving hundreds of
tonnes of zinc per year — with coating held within specification.
""")
    st.markdown(f'<span class="pill">model: {os.path.basename(MODEL_PATH)}</span>'
                f'<span class="pill">trained {bundle.get("trained_at","?")}</span>'
                f'<span class="pill">conformal q90 = {bundle.get("conformal_q90",0):.1f} g/m²</span>'
                f'<span class="pill">{len(bundle["features"])} features</span>'
                f'<span class="pill">best R² = {best["R2"]:.4f}</span>', unsafe_allow_html=True)

# ============================== TAB 6 — ABOUT ========================================
with tabs[5]:
    st.subheader("About this project")
    st.markdown("""
**Smart Zinc Coating Optimization using AI-based Modelling** restores automatic, on-target
coating control on a hot-dip galvanizing line — entirely in software — after the physical coating gauge became
unavailable. It combines IoT data acquisition, a physics-backed digital twin, a rigorously selected machine-learning
soft sensor (**PG-HGBT**) and model-predictive control, delivering auditable, quantified zinc savings.

- **Artefacts:** manuscript (IEEE TII), Colab notebook (EDA + 16-model benchmark + export), and this app.

*Engineering demonstration. The 3-D scene is an illustrative emulator; figures derive from the project dataset.
Replace with site data and photography for audited use.*
""")
    st.caption("© SAIL CRM-III — internal technical demonstration.")
