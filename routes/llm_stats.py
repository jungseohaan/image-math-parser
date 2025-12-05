# routes/llm_stats.py
"""LLM 사용량 통계 API"""

from flask import Blueprint, jsonify
from llm_tracker import tracker

llm_stats_bp = Blueprint('llm_stats', __name__)


@llm_stats_bp.route('/llm-stats', methods=['GET'])
def get_llm_stats():
    """LLM API 사용량 통계를 반환합니다."""
    return jsonify({
        "success": True,
        "stats": tracker.get_stats()
    })


@llm_stats_bp.route('/llm-stats/reset', methods=['POST'])
def reset_llm_stats():
    """LLM API 사용량 통계를 초기화합니다."""
    tracker.reset_stats()
    return jsonify({
        "success": True,
        "message": "통계가 초기화되었습니다.",
        "stats": tracker.get_stats()
    })


@llm_stats_bp.route('/llm-stats/summary', methods=['GET'])
def get_llm_summary():
    """LLM API 사용량 요약을 텍스트로 반환합니다."""
    return jsonify({
        "success": True,
        "summary": tracker.get_summary()
    })
