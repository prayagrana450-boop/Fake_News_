from __future__ import annotations

from flask import Blueprint, render_template

from utils.decorators import admin_required
from utils.model_evaluation import evaluate_models_safely


evaluation_bp = Blueprint("evaluation", __name__)


@evaluation_bp.route("/admin/evaluation")
@admin_required
def evaluation_page():
    payload = evaluate_models_safely()
    return render_template(
        "evaluation.html",
        results=payload.get("results", {}),
        error=payload.get("error"),
    )

