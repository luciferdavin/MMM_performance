"""Model diagnostics — convergence, R², MAPE."""
from __future__ import annotations
import numpy as np
import logging

logger = logging.getLogger(__name__)


def compute_diagnostics(model, y: "pd.Series", X: "pd.DataFrame", name: str, warnings: list[str] | None = None) -> "ModelDiagnostics":
    from mmm.models.schemas import ModelDiagnostics
    if warnings is None:
        warnings = []
    rhat_max = 1.1
    converged = True
    try:
        if hasattr(model, "posterior") and model.posterior is not None:
            import arviz as az
            summary = az.summary(model.posterior, var_names=["beta_channel"])
            if summary is not None and hasattr(summary, "r_hat"):
                rhat_max = float(summary["r_hat"].max())
                converged = bool(rhat_max < 1.1)
    except Exception:
        logger.warning("rhat computation failed; defaulting to 1.1")

    # R²
    r2 = 0.0
    mape = 0.0
    try:
        pred = model.predict(X)
        pred_np = pred.values.flatten() if hasattr(pred, "values") else np.array(pred)
        y_np = y.values.astype(float) if hasattr(y, "values") else np.array(y, dtype=float)
        ss_res = float(np.sum((y_np - pred_np) ** 2))
        ss_tot = float(np.sum((y_np - y_np.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        mape = float(np.mean(np.abs((y_np - pred_np) / np.where(y_np == 0, 1, y_np)))) * 100
    except Exception:
        logger.warning("R²/MAPE computation failed")
    if not converged:
        warnings.append(f"R-hat max={rhat_max:.3f} >= 1.1; model did not converge")
    if r2 < 0.3:
        warnings.append(f"low R² ({r2:.3f}); check data quality and channel coverage")
    return ModelDiagnostics(model_name=name, converged=converged, rhat_max=rhat_max, r2=r2, mape=mape, warnings=warnings)
