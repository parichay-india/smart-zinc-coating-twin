"""Load the PG-HGBT bundle and run predictions with a calibrated conformal uncertainty band."""
import warnings
import numpy as np
import joblib

try:  # silence the harmless sklearn pickle-version notice on Streamlit Cloud
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.simplefilter("ignore", InconsistentVersionWarning)
except Exception:
    pass

# Typical operating values for features not exposed on the UI (plant-data medians),
# so a handful of sliders are enough to drive the full model.
DEFAULTS = dict(processSpeed=86.0, width=1007.0, thickness=0.8,
                frontPressure=29.6, rearPressure=29.6, frontHP=18.4, rearHP=18.4,
                vPos=472.0, frontTilt=0.0, rearTilt=0.0, potTemp=462.0, snoutTemp=505.0)


def load_bundle(path):
    """Return the model bundle dict (model, features, target, conformal_q90, phys_coef, phys_vars, benchmark...)."""
    return joblib.load(path)


def _physics_feature(bundle, x):
    """Calibrated power-law physics-implied coating, computed exactly as in training."""
    coef = bundle.get("phys_coef", [-5.8141, 0.5787, -0.3097, 2.8825, 0.0691])
    pv = bundle.get("phys_vars", ["processSpeed", "frontPressure", "frontHP", "width"])
    vals = [max(float(x[v]), 1e-3) for v in pv]
    z = coef[0] + sum(c * np.log(v) for c, v in zip(coef[1:], vals))
    return float(np.clip(np.exp(z), 20.0, 320.0))


def build_vector(bundle, inputs):
    """Assemble the model input row in the exact feature order the model was trained on."""
    x = DEFAULTS.copy()
    x.update({k: float(v) for k, v in inputs.items() if v is not None})
    x.setdefault("rearPressure", x["frontPressure"])
    x.setdefault("rearHP", x["frontHP"])
    if "frontPressure" in inputs:   # mirror unless the caller set them explicitly
        x["rearPressure"] = float(inputs.get("rearPressure", x["frontPressure"]))
    if "frontHP" in inputs:
        x["rearHP"] = float(inputs.get("rearHP", x["frontHP"]))
    x["m_phys"] = _physics_feature(bundle, x)
    vec = np.array([[x[f] for f in bundle["features"]]], dtype=float)
    return vec, x


def predict(bundle, inputs):
    """Return (point, lower, upper) coating prediction with the 90% conformal band."""
    vec, _ = build_vector(bundle, inputs)
    yhat = float(bundle["model"].predict(vec)[0])
    q = float(bundle.get("conformal_q90", 0.0))
    return yhat, yhat - q, yhat + q
