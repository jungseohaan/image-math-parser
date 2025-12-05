# routes 패키지
from flask import Blueprint

# 블루프린트 등록 함수
def register_blueprints(app):
    """모든 블루프린트를 앱에 등록합니다."""
    from .llm_stats import llm_stats_bp
    from .prompts import prompts_bp

    app.register_blueprint(llm_stats_bp)
    app.register_blueprint(prompts_bp)
