"""Calibrated air-knife wiping physics for the hot-dip galvanizing digital twin.

The coating weight left on the strip after jet wiping is governed by four variables:
line (withdrawal) speed v, air-knife stagnation pressure p, knife-to-strip stand-off h,
and strip width w. A reduced-order wiping balance gives a log-linear (power-law) surrogate

    ln m_phys = c0 + c1 ln v + c2 ln p + c3 ln h + c4 ln w ,

with c1, c3 > 0 (coating rises with speed and stand-off) and c2 < 0 (coating falls with
pressure). The coefficients below are CALIBRATED on the plant data (constrained least
squares in log space); they reproduce the median operating coating and explain ~0.76 of the
coating variance on their own. This is the physical backbone of the grey-box twin: the
PG-HGBT model uses m_phys as a feature and learns the residual the physics does not capture.
"""
import numpy as np

# Calibrated power-law coefficients  [c0, c1(ln speed), c2(ln pressure), c3(ln stand-off), c4(ln width)]
PHYS_COEF = [-5.8141, 0.5787, -0.3097, 2.8825, 0.0691]
PHYS_VARS = ["processSpeed", "frontPressure", "frontHP", "width"]

# Reference operating point (plant medians) used for the explainability decomposition.
REF = dict(speed=86.0, pressure=29.6, gap=18.4, width=1007.0)


def m_phys(speed, pressure, gap, width=1007.0, coef=PHYS_COEF):
    """Calibrated physics-implied coating estimate (g/m^2) — the physics feature inside PG-HGBT."""
    speed = max(float(speed), 1e-3); pressure = max(float(pressure), 1e-3)
    gap = max(float(gap), 1e-3); width = max(float(width), 1e-3)
    z = (coef[0] + coef[1]*np.log(speed) + coef[2]*np.log(pressure)
         + coef[3]*np.log(gap) + coef[4]*np.log(width))
    return float(np.clip(np.exp(z), 20.0, 320.0))


def forward_coating(speed, pressure, gap, width=1007.0, thickness=0.8):
    """Physics forward model -> per-side coating weight (g/m^2). Thickness kept for signature compatibility."""
    return m_phys(speed, pressure, gap, width)


def recommend_pressure(target, speed, gap, width=1007.0, lo=6.0, hi=60.0):
    """Bisection for the minimum-zinc air-knife pressure that meets the coating target.

    Coating decreases monotonically with pressure, so the pressure landing exactly on target
    is the least zinc that still satisfies the specification -- the set-point the MPC seeks.
    """
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if forward_coating(speed, mid, gap, width) > target:
            lo = mid          # still over target -> raise pressure (wipe harder)
        else:
            hi = mid
    return 0.5 * (lo + hi)


def contributions(speed, pressure, gap, width=1007.0):
    """Per-variable coating deltas from the reference point (for the physics explainer)."""
    base = forward_coating(REF["speed"], REF["pressure"], REF["gap"], width)
    return {
        "baseline": base,
        "speed":    forward_coating(speed, REF["pressure"], REF["gap"], width) - base,
        "pressure": forward_coating(REF["speed"], pressure, REF["gap"], width) - base,
        "gap":      forward_coating(REF["speed"], REF["pressure"], gap, width) - base,
    }
