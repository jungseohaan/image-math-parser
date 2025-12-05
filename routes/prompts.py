# routes/prompts.py
"""프롬프트 관리 API"""

import os
from flask import Blueprint, jsonify, request, current_app

prompts_bp = Blueprint('prompts', __name__)

DEFAULT_SYSTEM_PROMPT = """이 시험지 이미지를 분석하여 모든 문항의 구조화된 정보를 추출해주세요.

다음 JSON 형식으로 응답해주세요:
{
  "questions": [
    {
      "question_number": "문항 번호 (예: 1, 2, 15 등)",
      "question_text": "문제 본문 텍스트 (수식은 LaTeX로 $..$ 또는 $$..$$ 형식으로 포함)",
      "has_passage": true/false,
      "passage": "지문이 있다면 지문 내용 (수식 포함, 원문 그대로)",
      "choices": [
        {"number": "①", "text": "선택지 1 내용 (수식 포함)"},
        {"number": "②", "text": "선택지 2 내용 (수식 포함)"},
        {"number": "③", "text": "선택지 3 내용 (수식 포함)"},
        {"number": "④", "text": "선택지 4 내용 (수식 포함)"},
        {"number": "⑤", "text": "선택지 5 내용 (수식 포함)"}
      ],
      "has_figure": true/false,
      "figure_description": "그림이나 도표가 있다면 설명",
      "has_table": true/false,
      "table_data": "표가 있다면 표 내용을 마크다운 형식으로",
      "math_expressions": ["문항에 포함된 주요 수식들을 LaTeX로 추출"],
      "question_type": "객관식/주관식/단답형/서술형 중 하나",
      "bounding_box": {
        "x": 0.0,
        "y": 0.0,
        "width": 1.0,
        "height": 1.0
      }
    }
  ]
}

중요 - 수식 변환 규칙:
- 모든 텍스트(문제, 지문, 선택지)에서 수식은 반드시 LaTeX로 변환
- 인라인 수식: $x^2 + y^2 = r^2$
- 블록 수식: $$\\int_0^1 f(x) dx$$
- 분수: $\\frac{a}{b}$, 루트: $\\sqrt{x}$, 적분: $\\int$, 시그마: $\\sum$
- 지수: $x^2$, 아래첨자: $x_1$
- 그리스 문자: $\\alpha$, $\\beta$, $\\theta$ 등
- 원문의 수식을 빠뜨리지 말고 모두 LaTeX로 변환해주세요

bounding_box 추출 규칙:
- 각 문항의 위치를 bounding_box로 지정해주세요
- x, y는 문항 영역의 왼쪽 상단 좌표 (0.0~1.0 비율)
- width, height는 문항 영역의 크기 (0.0~1.0 비율)
- 이미지 전체가 하나의 문항이면 x=0, y=0, width=1, height=1
- 여러 문항이 있을 때는 각 문항의 실제 영역을 정확히 지정

기타 주의사항:
- 이미지에 있는 모든 문항을 분석해주세요
- 지문(passage)은 박스나 인용문 형태의 텍스트이며, 원문 그대로 수식 포함하여 추출
- 선택지가 없으면 빈 배열 []로
- 없는 항목은 null 또는 빈 값으로 처리
- 문항이 여러 개인 경우 questions 배열에 모두 포함"""

DEFAULT_USER_PROMPT = ""


def _get_prompt_paths():
    """프롬프트 파일 경로들을 반환합니다."""
    config_folder = current_app.config.get('CONFIG_FOLDER', 'config')
    return {
        'system': os.path.join(config_folder, 'system_prompt.txt'),
        'user': os.path.join(config_folder, 'user_prompt.txt')
    }


def load_prompt(file_path, default_value):
    """파일에서 프롬프트를 로드합니다."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return default_value


def save_prompt(file_path, content):
    """프롬프트를 파일에 저장합니다."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def get_system_prompt():
    """시스템 프롬프트를 반환합니다."""
    paths = _get_prompt_paths()
    return load_prompt(paths['system'], DEFAULT_SYSTEM_PROMPT)


def get_user_prompt():
    """사용자 프롬프트를 반환합니다."""
    paths = _get_prompt_paths()
    return load_prompt(paths['user'], DEFAULT_USER_PROMPT)


@prompts_bp.route('/prompts', methods=['GET'])
def get_prompts():
    """시스템 프롬프트와 사용자 프롬프트를 반환합니다."""
    return jsonify({
        "success": True,
        "system_prompt": get_system_prompt(),
        "user_prompt": get_user_prompt(),
        "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
        "default_user_prompt": DEFAULT_USER_PROMPT
    })


@prompts_bp.route('/prompts', methods=['POST'])
def save_prompts():
    """시스템 프롬프트와 사용자 프롬프트를 저장합니다."""
    data = request.get_json()
    paths = _get_prompt_paths()

    if 'system_prompt' in data:
        save_prompt(paths['system'], data['system_prompt'])

    if 'user_prompt' in data:
        save_prompt(paths['user'], data['user_prompt'])

    return jsonify({
        "success": True,
        "message": "프롬프트가 저장되었습니다.",
        "system_prompt": get_system_prompt(),
        "user_prompt": get_user_prompt()
    })


@prompts_bp.route('/prompts/reset', methods=['POST'])
def reset_prompts():
    """프롬프트를 기본값으로 초기화합니다."""
    data = request.get_json() or {}
    reset_type = data.get('type', 'all')  # 'system', 'user', 'all'
    paths = _get_prompt_paths()

    if reset_type in ['system', 'all']:
        if os.path.exists(paths['system']):
            os.remove(paths['system'])

    if reset_type in ['user', 'all']:
        if os.path.exists(paths['user']):
            os.remove(paths['user'])

    return jsonify({
        "success": True,
        "message": "프롬프트가 초기화되었습니다.",
        "system_prompt": get_system_prompt(),
        "user_prompt": get_user_prompt()
    })
