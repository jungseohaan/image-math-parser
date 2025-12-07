# generate_variants.py
"""
변형 문제 생성기: 원본 문제를 기반으로 난이도별 변형 문제를 생성합니다.
검증 및 그래프 시각화 기능 포함.
"""

import os
import json
import re
import base64
import io
import time
import google.generativeai as genai
from datetime import datetime
from llm_tracker import tracker


def format_number(value) -> str:
    """
    숫자를 깔끔하게 포맷팅합니다.
    - 긴 소수점을 2자리로 반올림
    - 정수는 그대로 유지
    - 문자열은 그대로 반환
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # 정수에 가까우면 정수로 변환
        if value == int(value):
            return str(int(value))
        # 소수점 2자리로 반올림
        rounded = round(value, 2)
        # 반올림 후 정수가 되면 정수로
        if rounded == int(rounded):
            return str(int(rounded))
        return str(rounded)
    # sympy 객체 등 다른 타입
    try:
        # sympy Float 등을 처리
        float_val = float(value)
        if float_val == int(float_val):
            return str(int(float_val))
        rounded = round(float_val, 2)
        if rounded == int(rounded):
            return str(int(rounded))
        return str(rounded)
    except (ValueError, TypeError):
        return str(value)


def format_variant_numbers(variant: dict) -> dict:
    """
    변형 문제의 모든 숫자 값을 깔끔하게 포맷팅합니다.
    """
    if not isinstance(variant, dict):
        return variant

    # choices 포맷팅
    if 'choices' in variant and isinstance(variant['choices'], list):
        for choice in variant['choices']:
            if isinstance(choice, dict) and 'text' in choice:
                choice['text'] = format_number(choice['text'])

    # answer 포맷팅 (숫자인 경우)
    if 'answer' in variant:
        answer = variant['answer']
        # ①②③④⑤ 형태가 아닌 경우에만 포맷팅
        if answer and not any(c in str(answer) for c in '①②③④⑤'):
            variant['answer'] = format_number(answer)

    return variant


def fix_json_string(text: str) -> str:
    """
    LLM 응답에서 JSON 파싱 오류를 일으킬 수 있는 문자열을 수정합니다.
    특히 LaTeX 수식의 백슬래시를 적절히 이스케이프합니다.
    """
    # JSON 문자열 내부의 잘못된 이스케이프 시퀀스 수정
    # 백슬래시 뒤에 유효하지 않은 이스케이프 문자가 오는 경우 이중 백슬래시로 변경

    result = []
    in_string = False
    i = 0

    while i < len(text):
        char = text[i]

        # 문자열 시작/종료 감지 (이스케이프되지 않은 따옴표)
        if char == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        # 문자열 내부에서 백슬래시 처리
        if in_string and char == '\\' and i + 1 < len(text):
            next_char = text[i + 1]
            # 유효한 JSON 이스케이프 시퀀스: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
            valid_escapes = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}

            if next_char not in valid_escapes:
                # LaTeX 명령어 등의 무효한 이스케이프 -> 백슬래시를 이중으로
                result.append('\\\\')
                i += 1
                continue

        result.append(char)
        i += 1

    return ''.join(result)


def safe_json_loads(text: str) -> dict:
    """
    안전하게 JSON을 파싱합니다. 실패 시 여러 복구 전략을 시도합니다.
    """
    # 1차 시도: 직접 파싱
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2차 시도: 이스케이프 수정 후 파싱
    try:
        fixed = fix_json_string(text)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 3차 시도: 제어 문자 제거 후 파싱
    try:
        # 제어 문자 제거 (탭, 개행 제외)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 4차 시도: 줄바꿈을 \\n으로 변환 후 파싱
    try:
        # JSON 문자열 내의 실제 줄바꿈을 이스케이프된 줄바꿈으로 변환
        fixed = re.sub(r'(?<!\\)\\n', r'\\\\n', text)
        fixed = fix_json_string(fixed)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 5차 시도: 문자열 내의 줄바꿈을 공백으로 변환
    try:
        # JSON 문자열 안의 줄바꿈을 처리
        def replace_newlines_in_strings(match):
            content = match.group(1)
            # 실제 줄바꿈을 공백으로 변환
            content = content.replace('\n', ' ').replace('\r', ' ')
            return f'"{content}"'

        # 문자열 패턴 매칭하여 내부 줄바꿈 처리
        fixed = re.sub(r'"((?:[^"\\]|\\.)*)(?:\n|\r\n?)([^"]*)"',
                       lambda m: f'"{m.group(1)} {m.group(2)}"', text)
        return json.loads(fixed)
    except (json.JSONDecodeError, re.error):
        pass

    # 모든 시도 실패 시 원본 오류 발생
    return json.loads(text)

# .env 파일에서 환경 변수 로드
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

# Gemini API 설정
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
genai.configure(api_key=GEMINI_API_KEY)

VARIANT_PROMPT = """당신은 교육 전문가입니다. 주어진 원본 문제를 바탕으로 변형 문제를 생성해주세요.

## 원본 문제
{original_question}

## 요청사항
위 원본 문제를 기반으로 다음 난이도별로 변형 문제를 생성해주세요:

1. **쉬움 (3문제)**: 원본보다 쉬운 난이도. 개념을 단순화하거나, 숫자를 간단하게 변경
2. **보통 (4문제)**: 원본과 비슷한 난이도. 숫자나 상황만 변경
3. **어려움 (3문제)**: 원본보다 어려운 난이도. 추가 조건이나 복잡한 계산 포함

## 그래프/도표 생성 규칙 (매우 중요!)
문제를 시각화할 수 있는 경우, 반드시 graph_info를 포함해주세요:

### 지원하는 그래프 유형
1. **function**: 함수 그래프 (일차함수, 이차함수, 삼각함수, 지수/로그 등)
   - function: 파이썬 numpy 문법 (예: "2*x + 1", "x**2 - 3*x + 2", "sin(x)", "exp(x)")
   - x_range, y_range: 범위 지정
   - points: 강조할 점들 [[x, y], ...]
   - asymptotes: 점근선 [x값, ...] 또는 {{horizontal: y값, vertical: [x값]}}

2. **geometry**: 기하 도형 (삼각형, 사각형, 원, 다각형 등)
   - shapes: 도형 목록
     - 삼각형/다각형: {{"type": "polygon", "points": [[x,y],...], "labels": ["A","B","C"]}}
     - 원: {{"type": "circle", "center": [x,y], "radius": r, "label": "O"}}
     - 선분: {{"type": "line", "start": [x,y], "end": [x,y], "label": "AB"}}
     - 호: {{"type": "arc", "center": [x,y], "radius": r, "start_angle": 0, "end_angle": 90}}
   - annotations: 각도, 길이 표시 [{{"type": "angle", "vertex": [x,y], "value": "60°"}}]

3. **statistics**: 통계 그래프 (막대, 원, 히스토그램, 상자그림 등)
   - chart_type: "bar", "pie", "histogram", "boxplot", "scatter", "line"
   - data: 데이터 값 목록
   - labels: 라벨 목록
   - title: 차트 제목
   - colors: 색상 목록 (선택)

4. **coordinate**: 좌표평면 위의 점/벡터
   - points: [[x, y], ...] 점 목록
   - labels: ["A", "B", ...] 라벨
   - vectors: [{{"start": [x,y], "end": [x,y], "label": "v"}}] 벡터
   - regions: 영역 표시 (부등식 등)

5. **sequence**: 수열 시각화
   - terms: [a1, a2, a3, ...] 수열 항들
   - formula: "수열 공식 설명"
   - show_sum: true/false 합계 표시

6. **number_line**: 수직선
   - points: [값, ...] 표시할 점
   - labels: ["A", ...] 라벨
   - intervals: [{{"start": a, "end": b, "open_start": false, "open_end": true}}] 구간

7. **region**: 두 곡선 사이의 영역 (적분, 넓이 문제)
   - functions: ["x**2 + 3", "-1/5*x**2 + 3"] 두 개 이상의 함수식
   - x_range: [0, 2] 영역의 x 범위
   - y_range: [-1, 15] y축 표시 범위 (선택)
   - vertical_lines: [2] 수직선 x값들 (선택)
   - fill_between: [0, 1] 채울 함수 인덱스 (선택, 기본값 [0, 1])
   - points: [[x, y, "label"], ...] 강조할 점들 (선택)
   - colors: ["blue", "red", ...] 함수별 색상 (선택)

## 출력 형식 (JSON)
```json
{{
  "original": {{
    "question_number": "원본 문제 번호",
    "question_text": "원본 문제 텍스트 (수식은 LaTeX)",
    "choices": [{{"number": "①", "text": "선택지"}}],
    "answer": "정답 번호 (예: ①)",
    "explanation": "[풀이]\n사용 개념: (핵심 공식/정리)\n$수식 전개 과정$\n$계산: ... = 결과$\n∴ 정답: ①",
    "graph_info": {{
      "type": "function/geometry/statistics/coordinate/sequence/number_line/region/venn/none",
      "description": "이 그래프가 무엇을 보여주는지 설명",
      "show_in_question": true,
      "plot_data": {{ ... }}
    }}
  }},
  "variants": [
    {{
      "variant_id": 1,
      "difficulty": "쉬움",
      "question_text": "변형 문제 텍스트 (수식은 LaTeX)",
      "choices": [{{"number": "①", "text": "선택지"}}],
      "answer": "정답 번호",
      "explanation": "[풀이]\n사용 개념: (핵심 공식/정리)\n$수식 전개 과정$\n$계산: ... = 결과$\n∴ 정답: ①",
      "change_description": "원본과 어떻게 다른지 설명",
      "graph_info": {{
        "type": "function/geometry/statistics/coordinate/sequence/number_line/region/venn/none",
        "description": "그래프 설명",
        "show_in_question": true,
        "plot_data": {{ ... }}
      }}
    }}
  ]
}}
```

중요:
- 모든 수식은 LaTeX 형식 ($..$ 또는 $$..$$)으로 작성
- 변형 문제도 원본과 동일한 유형(객관식/주관식)을 유지
- 각 변형 문제의 정답과 풀이 과정을 반드시 포함
- **풀이 과정(explanation) 작성 규칙**:
  - 사용한 핵심 개념/공식을 먼저 명시
  - 수식 전개와 계산 과정을 LaTeX로 표현
  - 중복 설명 없이 논리적 흐름만 유지
  - 예: "[풀이]\n사용 개념: 중복조합 $_nH_r = _{n+r-1}C_r$\n$_3H_4 = _6C_4 = 15$\n∴ 정답: 15"
- **그래프로 표현 가능한 문제는 반드시 graph_info에 plot_data 포함**
- show_in_question: true면 문제 영역에도 그래프 표시, false면 풀이에만 표시
- 함수는 파이썬 numpy 문법으로 (^대신 **, sin/cos/exp/log/sqrt/abs/pi 사용)
- **확률/집합 문제는 벤다이어그램(venn)으로 시각화**
  - type: "venn"
  - plot_data 예시: {{"universal": {{"label": "U"}}, "sets": [{{"cx": -0.7, "cy": 0, "r": 1.2, "label": "A"}}, {{"cx": 0.7, "cy": 0, "r": 1.2, "label": "B"}}], "values": [{{"x": -1.2, "y": 0, "value": "10"}}, {{"x": 0, "y": 0, "value": "5"}}, {{"x": 1.2, "y": 0, "value": "8"}}]}}
- 그래프가 불필요하면 graph_info.type을 "none"으로
- JSON 형식만 출력 (다른 텍스트 없이)
"""

VERIFY_PROMPT = """다음 수학/과학 문제를 직접 풀어서 정답을 검증해주세요.

## 문제
{question_text}

## 선택지
{choices}

## 주어진 정답
{claimed_answer}

## 주어진 풀이
{claimed_explanation}

**중요: 문제를 직접 풀어주세요.**

다음 JSON 형식으로 응답해주세요:
```json
{{
  "is_correct": true/false,
  "verified_answer": "검증된 정답 (예: ①, ②, 또는 숫자)",
  "verification_steps": "핵심 풀이 과정 요약",
  "detailed_solution": "[풀이]\n사용 개념: (공식/정리)\n$수식 전개$\n$계산 과정$\n∴ 정답: ...",
  "confidence": "high/medium/low",
  "key_formula": "핵심 공식/개념"
}}
```
"""


def solve_original_question(question_data: dict) -> dict:
    """원본 문제를 LLM으로 풀이하여 정답과 풀이 과정을 생성합니다."""
    model_name = 'gemini-2.0-flash'

    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.3,
    }

    model = genai.GenerativeModel(model_name, generation_config=generation_config)

    # 문제 텍스트 구성
    question_text = question_data.get('question_text', '')
    choices = question_data.get('choices', [])
    question_type = question_data.get('question_type', '객관식')

    choices_text = ""
    if choices:
        for choice in choices:
            choices_text += f"\n{choice.get('number', '')} {choice.get('text', '')}"

    prompt = f"""다음 수학 문제를 풀고 정답과 상세한 풀이 과정을 제공해주세요.

## 문제
{question_text}

## 선택지{choices_text if choices else " (단답형 문제)"}

## 문제 유형
{question_type}

## 응답 형식 (JSON)
```json
{{
  "answer": "정답 (객관식: ①②③④⑤ 중 하나, 단답형: 숫자)",
  "explanation": "상세 풀이 과정 (단계별로 설명, LaTeX 수식 사용)",
  "key_concepts": ["핵심 개념 목록"]
}}
```

풀이는 단계별로 명확하게 작성하고, 수식은 LaTeX ($...$ 또는 $$...$$)를 사용해주세요.
"""

    try:
        start_time = time.time()
        response = model.generate_content(prompt)
        latency_ms = (time.time() - start_time) * 1000

        text = response.text.strip()

        # 사용량 추적
        tracker.track_call(
            model=model_name,
            operation="solve_original",
            prompt=prompt,
            response_text=text,
            latency_ms=latency_ms,
            success=True
        )

        # JSON 파싱
        result = safe_json_loads(text)
        return result

    except Exception as e:
        print(f"원본 문제 풀이 생성 실패: {e}")
        return {
            "answer": "",
            "explanation": "",
            "key_concepts": []
        }


def verify_answer(question_text: str, choices: list, claimed_answer: str, claimed_explanation: str) -> dict:
    """LLM을 사용하여 정답을 검증합니다."""
    model_name = 'gemini-2.0-flash'

    # JSON 모드 설정
    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.3,
    }

    model = genai.GenerativeModel(
        model_name,
        generation_config=generation_config
    )

    choices_text = "\n".join([f"{c['number']} {c['text']}" for c in choices]) if choices else "선택지 없음"

    prompt = VERIFY_PROMPT.format(
        question_text=question_text,
        choices=choices_text,
        claimed_answer=claimed_answer,
        claimed_explanation=claimed_explanation
    )

    start_time = time.time()
    try:
        response = model.generate_content(prompt)
        latency_ms = (time.time() - start_time) * 1000
        text = response.text.strip()

        # 사용량 추적
        tracker.track_call(
            model=model_name,
            operation="verify_answer",
            prompt=prompt,
            response_text=text,
            latency_ms=latency_ms,
            success=True
        )

        # JSON 모드에서는 직접 파싱
        return json.loads(text)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        tracker.track_call(
            model=model_name,
            operation="verify_answer",
            prompt=prompt,
            response_text="",
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        print(f"검증 오류: {e}")
        return {
            "is_correct": None,
            "verified_answer": claimed_answer,
            "verification_steps": f"검증 실패: {str(e)}",
            "confidence": "low"
        }


def generate_graph(graph_info: dict, output_path: str = None, variant_id: str = None) -> str:
    """그래프를 생성하고 base64 또는 파일 경로를 반환합니다.

    Args:
        graph_info: 그래프 정보 딕셔너리
        output_path: 파일 저장 경로 (지정하면 파일로 저장, 없으면 base64 반환)
        variant_id: 변형 문제 ID (선택, 현재 미사용)

    Returns:
        base64 데이터 URI 또는 저장된 파일 경로
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # 백엔드 설정
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.patches import FancyArrowPatch, Arc, Circle, Polygon
        import numpy as np

        # LaTeX 수식 렌더링 설정
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['mathtext.fontset'] = 'dejavusans'  # 수학 폰트 설정
        plt.rcParams['text.usetex'] = False  # LaTeX 엔진 사용 안함 (호환성)
        plt.rcParams['font.size'] = 11

        graph_type = graph_info.get('type', 'none')
        if graph_type == 'none':
            return None

        plot_data = graph_info.get('plot_data', {})
        if not plot_data:
            return None

        fig, ax = plt.subplots(figsize=(6, 5))
        plot_success = False

        # 수능 스타일: 흑백/회색 톤만 사용
        CURVE_COLOR = 'black'
        SHADE_COLOR = 'gray'
        SHADE_ALPHA = 0.3
        POINT_COLOR = 'black'
        DASHED_COLOR = 'black'

        if graph_type == 'function':
            # 함수 그래프
            func_str = plot_data.get('function', '')
            x_range = plot_data.get('x_range', [-10, 10])
            y_range = plot_data.get('y_range', None)

            if func_str:
                x = np.linspace(x_range[0], x_range[1], 400)
                try:
                    safe_dict = {
                        'x': x, 'np': np, 'sin': np.sin, 'cos': np.cos,
                        'tan': np.tan, 'exp': np.exp, 'log': np.log,
                        'sqrt': np.sqrt, 'abs': np.abs, 'pi': np.pi,
                        'e': np.e, 'log10': np.log10, 'log2': np.log2,
                        'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
                        'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
                        'floor': np.floor, 'ceil': np.ceil,
                        'where': np.where, 'maximum': np.maximum, 'minimum': np.minimum
                    }
                    eval_func_str = func_str
                    if '=' in eval_func_str:
                        eval_func_str = eval_func_str.split('=')[1].strip()
                    eval_func_str = eval_func_str.replace('^', '**')
                    if 'if' not in eval_func_str and '?' not in eval_func_str:
                        y = eval(eval_func_str, {"__builtins__": {}}, safe_dict)
                        if np.isscalar(y):
                            y = np.full_like(x, y)
                        # 수식 레이블 생성
                        display_func = func_str.replace('**', '^').replace('*', '')
                        display_func = display_func.replace('sqrt', r'\sqrt')
                        display_func = display_func.replace('pi', r'\pi')
                        ax.plot(x, y, color=CURVE_COLOR, linewidth=1.5)
                        # 곡선에 직접 레이블 표시 (수능 스타일: 심플하게)
                        label_x_idx = int(len(x) * 0.8)
                        label_x, label_y = x[label_x_idx], y[label_x_idx]
                        ax.annotate(f'$y=f(x)$', (label_x, label_y),
                                   textcoords="offset points", xytext=(5, 5),
                                   fontsize=11, color=CURVE_COLOR)
                        plot_success = True
                except Exception as e:
                    print(f"함수 그래프 오류: {e}")

            # 점근선 (수능 스타일: 검정 점선)
            asymptotes = plot_data.get('asymptotes', {})
            if isinstance(asymptotes, dict):
                for v_line in asymptotes.get('vertical', []):
                    ax.axvline(x=v_line, color=DASHED_COLOR, linestyle='--', linewidth=1)
                if 'horizontal' in asymptotes:
                    h_val = asymptotes['horizontal']
                    ax.axhline(y=h_val, color=DASHED_COLOR, linestyle='--', linewidth=1)
            elif isinstance(asymptotes, list):
                for v_line in asymptotes:
                    ax.axvline(x=v_line, color=DASHED_COLOR, linestyle='--', linewidth=1)

            # 점 표시 (수능 스타일: 검정 점)
            points = plot_data.get('points', [])
            labels = plot_data.get('labels', [])
            for i, point in enumerate(points):
                if len(point) >= 2:
                    ax.plot(point[0], point[1], 'ko', markersize=5, zorder=5)
                    label = labels[i] if i < len(labels) else f'({point[0]}, {point[1]})'
                    ax.annotate(label, (point[0], point[1]), textcoords="offset points",
                               xytext=(5, 5), fontsize=10, color=POINT_COLOR)
                    plot_success = True

            if y_range:
                ax.set_ylim(y_range)

        elif graph_type == 'geometry':
            # 기하 도형 (수능 스타일: 검정선, 회색 음영)
            shapes = plot_data.get('shapes', [])

            # 기존 points 형식 호환성
            if not shapes and plot_data.get('points'):
                shapes = [{"type": "polygon", "points": plot_data['points'], "labels": plot_data.get('labels', [])}]

            for shape in shapes:
                shape_type = shape.get('type', 'polygon')

                if shape_type == 'polygon':
                    points = shape.get('points', [])
                    labels = shape.get('labels', [])
                    if points:
                        xs = [p[0] for p in points] + [points[0][0]]
                        ys = [p[1] for p in points] + [points[0][1]]
                        ax.plot(xs, ys, color=CURVE_COLOR, linewidth=1.5)
                        ax.fill(xs, ys, alpha=SHADE_ALPHA, color=SHADE_COLOR)
                        for i, point in enumerate(points):
                            ax.plot(point[0], point[1], 'ko', markersize=4)
                            label = labels[i] if i < len(labels) else f'P{i+1}'
                            ax.annotate(label, (point[0], point[1]), textcoords="offset points",
                                       xytext=(5, 5), fontsize=11, color=POINT_COLOR)
                        plot_success = True

                elif shape_type == 'circle':
                    center = shape.get('center', [0, 0])
                    radius = shape.get('radius', 1)
                    label = shape.get('label', '')
                    circle = Circle(center, radius, fill=False, color=CURVE_COLOR, linewidth=1.5)
                    ax.add_patch(circle)
                    ax.plot(center[0], center[1], 'ko', markersize=3)
                    if label:
                        ax.annotate(label, center, textcoords="offset points",
                                   xytext=(5, 5), fontsize=11, color=POINT_COLOR)
                    plot_success = True

                elif shape_type == 'line':
                    start = shape.get('start', [0, 0])
                    end = shape.get('end', [1, 1])
                    label = shape.get('label', '')
                    ax.plot([start[0], end[0]], [start[1], end[1]], color=CURVE_COLOR, linewidth=1.5)
                    if label:
                        mid_x = (start[0] + end[0]) / 2
                        mid_y = (start[1] + end[1]) / 2
                        ax.annotate(label, (mid_x, mid_y), textcoords="offset points",
                                   xytext=(0, 8), fontsize=10, color=POINT_COLOR)
                    plot_success = True

                elif shape_type == 'arc':
                    center = shape.get('center', [0, 0])
                    radius = shape.get('radius', 1)
                    start_angle = shape.get('start_angle', 0)
                    end_angle = shape.get('end_angle', 90)
                    arc = Arc(center, radius*2, radius*2, angle=0,
                             theta1=start_angle, theta2=end_angle, color=CURVE_COLOR, linewidth=1.5)
                    ax.add_patch(arc)
                    plot_success = True

            # 주석 (각도, 길이 등) - 수능 스타일: 검정색
            annotations = plot_data.get('annotations', [])
            for ann in annotations:
                if ann.get('type') == 'angle':
                    vertex = ann.get('vertex', [0, 0])
                    value = ann.get('value', '')
                    ax.annotate(value, vertex, textcoords="offset points",
                               xytext=(10, 10), fontsize=10, color=POINT_COLOR)

            ax.set_aspect('equal')
            ax.autoscale()

        elif graph_type == 'statistics':
            # 통계 그래프 (수능 스타일: 회색 계열)
            data = plot_data.get('data', [])
            labels = plot_data.get('labels', [])
            chart_type = plot_data.get('chart_type', 'bar')
            title = plot_data.get('title', '')
            # 수능 스타일: 회색 계열 색상
            gray_colors = ['#666666', '#888888', '#aaaaaa', '#cccccc', '#444444']

            if chart_type == 'bar' and data:
                x_pos = range(len(data))
                bars = ax.bar(x_pos, data, color=gray_colors[:len(data)], edgecolor='black', linewidth=0.5)
                if labels:
                    ax.set_xticks(x_pos)
                    ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0)
                # 값 표시
                for bar, val in zip(bars, data):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                           str(val), ha='center', va='bottom', fontsize=9, color='black')
                plot_success = True

            elif chart_type == 'pie' and data:
                ax.pie(data, labels=labels, autopct='%1.1f%%', colors=gray_colors[:len(data)],
                      wedgeprops={'edgecolor': 'black', 'linewidth': 0.5})
                ax.axis('equal')
                plot_success = True

            elif chart_type == 'histogram' and data:
                ax.hist(data, bins=plot_data.get('bins', 10), color=SHADE_COLOR, edgecolor='black')
                plot_success = True

            elif chart_type == 'boxplot' and data:
                ax.boxplot(data, labels=labels if labels else None)
                plot_success = True

            elif chart_type == 'scatter' and data:
                if isinstance(data[0], (list, tuple)):
                    xs = [p[0] for p in data]
                    ys = [p[1] for p in data]
                    ax.scatter(xs, ys, c=POINT_COLOR, s=30)
                    for i, (x, y) in enumerate(zip(xs, ys)):
                        if i < len(labels):
                            ax.annotate(labels[i], (x, y), textcoords="offset points",
                                       xytext=(5, 5), fontsize=10, color=POINT_COLOR)
                    plot_success = True

            elif chart_type == 'line' and data:
                ax.plot(data, color=CURVE_COLOR, marker='o', linewidth=1.5, markersize=4)
                if labels:
                    ax.set_xticks(range(len(labels)))
                    ax.set_xticklabels(labels)
                plot_success = True

            if title:
                ax.set_title(title, fontsize=12, pad=10, color='black')

        elif graph_type == 'coordinate':
            # 좌표평면 위의 점/벡터 (수능 스타일)
            points = plot_data.get('points', [])
            labels = plot_data.get('labels', [])
            vectors = plot_data.get('vectors', [])

            # 점 표시 (수능 스타일: 검정 점)
            for i, point in enumerate(points):
                if len(point) >= 2:
                    ax.plot(point[0], point[1], 'ko', markersize=5)
                    label = labels[i] if i < len(labels) else f'({point[0]}, {point[1]})'
                    ax.annotate(label, (point[0], point[1]), textcoords="offset points",
                               xytext=(5, 5), fontsize=11, color=POINT_COLOR)
                    plot_success = True

            # 벡터 표시 (수능 스타일: 검정 화살표)
            for vec in vectors:
                start = vec.get('start', [0, 0])
                end = vec.get('end', [1, 1])
                label = vec.get('label', '')
                ax.annotate('', xy=end, xytext=start,
                           arrowprops=dict(arrowstyle='->', color=CURVE_COLOR, lw=1.5))
                if label:
                    mid_x = (start[0] + end[0]) / 2
                    mid_y = (start[1] + end[1]) / 2
                    ax.annotate(label, (mid_x, mid_y), textcoords="offset points",
                               xytext=(5, 5), fontsize=10, color=POINT_COLOR)
                plot_success = True

            ax.set_aspect('equal')

        elif graph_type == 'sequence':
            # 수열 시각화 (수능 스타일)
            terms = plot_data.get('terms', [])
            formula = plot_data.get('formula', '')
            show_sum = plot_data.get('show_sum', False)

            if terms:
                n_values = range(1, len(terms) + 1)
                # 수능 스타일: 검정색 stem 플롯
                markerline, stemlines, baseline = ax.stem(n_values, terms, linefmt='k-', markerfmt='ko', basefmt='k-')
                plt.setp(markerline, markersize=5)
                plt.setp(stemlines, linewidth=1)
                for n, term in zip(n_values, terms):
                    ax.annotate(f'$a_{{{n}}}={term}$', (n, term), textcoords="offset points",
                               xytext=(5, 8), fontsize=10, color=POINT_COLOR)

                if show_sum:
                    cumsum = np.cumsum(terms)
                    ax.plot(n_values, cumsum, color=CURVE_COLOR, linestyle='--', marker='s',
                           linewidth=1, markersize=4)
                    # 누적합 직접 레이블
                    last_n = list(n_values)[-1]
                    last_sum = cumsum[-1]
                    ax.annotate(r'$S_n$', (last_n, last_sum),
                               textcoords="offset points", xytext=(8, 0),
                               fontsize=10, color=POINT_COLOR)

                # 눈금과 숫자 제거
                ax.set_xticks([])
                ax.set_yticks([])

                # 축 끝에 직접 n, a_n 레이블 표시
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                n_lim = ax.get_xlim()
                a_lim = ax.get_ylim()
                ax.annotate('$n$', xy=(n_lim[1], 0), xytext=(n_lim[1] + 0.2, 0),
                           fontsize=14, ha='left', va='center')
                ax.annotate('$a_n$', xy=(0, a_lim[1]), xytext=(0, a_lim[1] + 0.2),
                           fontsize=14, ha='center', va='bottom')
                if formula:
                    # formula가 $ 기호를 포함하지 않으면 추가
                    if '$' not in formula:
                        formula = f'${formula}$'
                    ax.set_title(f'수열: {formula}', fontsize=12)
                plot_success = True

        elif graph_type == 'number_line':
            # 수직선 (수능 스타일)
            points_data = plot_data.get('points', [])
            labels = plot_data.get('labels', [])
            intervals = plot_data.get('intervals', [])

            # 범위 계산
            all_points = list(points_data)
            for interval in intervals:
                all_points.extend([interval.get('start', 0), interval.get('end', 1)])

            if all_points:
                min_val = min(all_points) - 1
                max_val = max(all_points) + 1
            else:
                min_val, max_val = -5, 5

            # 수직선 그리기 (수능 스타일: 검정 선)
            ax.axhline(y=0, color='black', linewidth=1.5)
            ax.set_xlim(min_val, max_val)
            ax.set_ylim(-0.5, 0.5)

            # 눈금 (수능 스타일: 검정)
            tick_vals = range(int(min_val), int(max_val) + 1)
            for t in tick_vals:
                ax.plot([t, t], [-0.08, 0.08], 'k-', linewidth=1)
                ax.text(t, -0.2, str(t), ha='center', fontsize=10, color='black')

            # 구간 표시 (수능 스타일: 회색)
            for interval in intervals:
                start = interval.get('start', 0)
                end = interval.get('end', 1)
                open_start = interval.get('open_start', False)
                open_end = interval.get('open_end', False)

                ax.plot([start, end], [0, 0], color=SHADE_COLOR, linewidth=3, alpha=0.6)
                ax.plot(start, 0, 'ko',
                       markersize=6, markerfacecolor='black' if not open_start else 'white',
                       markeredgecolor='black', markeredgewidth=1.5)
                ax.plot(end, 0, 'ko',
                       markersize=6, markerfacecolor='black' if not open_end else 'white',
                       markeredgecolor='black', markeredgewidth=1.5)

            # 점 표시 (수능 스타일: 검정 점)
            for i, p in enumerate(points_data):
                ax.plot(p, 0, 'ko', markersize=5, zorder=5)
                label = labels[i] if i < len(labels) else str(p)
                ax.annotate(label, (p, 0), textcoords="offset points",
                           xytext=(0, 12), fontsize=11, ha='center', color='black')

            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            plot_success = True

        elif graph_type == 'region':
            # 두 곡선 사이의 영역 (수능 스타일: 검정 곡선, 회색 음영)
            functions = plot_data.get('functions', [])
            x_range = plot_data.get('x_range', [0, 2])
            y_range = plot_data.get('y_range', None)
            vertical_lines = plot_data.get('vertical_lines', [])
            fill_between_idx = plot_data.get('fill_between', [0, 1])
            points = plot_data.get('points', [])

            if functions and len(functions) >= 1:
                # x 범위 생성 (전체 그래프용)
                x_full = np.linspace(x_range[0] - 1, x_range[1] + 1, 400)
                # 영역 채우기용 x 범위
                x_fill = np.linspace(x_range[0], x_range[1], 200)

                safe_dict = {
                    'x': None, 'np': np, 'sin': np.sin, 'cos': np.cos,
                    'tan': np.tan, 'exp': np.exp, 'log': np.log,
                    'sqrt': np.sqrt, 'abs': np.abs, 'pi': np.pi,
                    'e': np.e, 'log10': np.log10, 'log2': np.log2
                }

                y_values_full = []
                y_values_fill = []
                labels_list = []

                for i, func_str in enumerate(functions):
                    try:
                        # 함수식 전처리
                        eval_func = func_str.replace('^', '**')

                        # 전체 범위 계산
                        safe_dict['x'] = x_full
                        y_full = eval(eval_func, {"__builtins__": {}}, safe_dict)
                        if np.isscalar(y_full):
                            y_full = np.full_like(x_full, y_full)
                        y_values_full.append(y_full)

                        # 채우기 범위 계산
                        safe_dict['x'] = x_fill
                        y_fill = eval(eval_func, {"__builtins__": {}}, safe_dict)
                        if np.isscalar(y_fill):
                            y_fill = np.full_like(x_fill, y_fill)
                        y_values_fill.append(y_fill)

                        # 라벨 생성: 실제 수식을 LaTeX 형식으로 변환
                        display_func = func_str.replace('**', '^').replace('*', '')
                        display_func = display_func.replace('sqrt', r'\sqrt')
                        display_func = display_func.replace('pi', r'\pi')
                        # x^2 -> x² 형태의 LaTeX
                        labels_list.append(f'$y={display_func}$')

                        # 곡선 그리기 (수능 스타일: 모두 검정)
                        ax.plot(x_full, y_full, color=CURVE_COLOR, linewidth=1.5)
                        plot_success = True
                    except Exception as e:
                        print(f"함수 {i} 오류: {e}")
                        continue

                # 각 곡선에 직접 레이블 표시 (수능 스타일: 심플하게)
                # 레이블 위치를 함수별로 다르게 해서 겹침 방지
                label_positions = [0.85, 0.15, 0.5, 0.3, 0.7]  # 각 함수의 x 위치 비율
                for i, (y_full, label_text) in enumerate(zip(y_values_full, labels_list)):
                    # 레이블 위치: 함수별로 다른 x 위치
                    pos_ratio = label_positions[i % len(label_positions)]
                    label_x_idx = int(len(x_full) * pos_ratio)
                    label_x = x_full[label_x_idx]
                    label_y = y_full[label_x_idx]
                    # 수능 스타일: 박스 없이 심플하게
                    ax.annotate(label_text, (label_x, label_y),
                               textcoords="offset points", xytext=(5, 5),
                               fontsize=10, color=CURVE_COLOR)

                # 두 곡선 사이 영역 채우기 (수능 스타일: 회색)
                if len(y_values_fill) >= 2:
                    # fill_between_idx가 리스트인지 딕셔너리인지 확인
                    if isinstance(fill_between_idx, list) and len(fill_between_idx) >= 2:
                        idx1, idx2 = fill_between_idx[0], fill_between_idx[1]
                    elif isinstance(fill_between_idx, dict):
                        idx1, idx2 = fill_between_idx.get(0, 0), fill_between_idx.get(1, 1)
                    else:
                        idx1, idx2 = 0, 1  # 기본값

                    if idx1 < len(y_values_fill) and idx2 < len(y_values_fill):
                        ax.fill_between(x_fill, y_values_fill[idx1], y_values_fill[idx2],
                                       alpha=SHADE_ALPHA, color=SHADE_COLOR)

                # 수직선 그리기 (수능 스타일: 검정 점선)
                for vline in vertical_lines:
                    ax.axvline(x=vline, color=DASHED_COLOR, linewidth=1, linestyle='--')

                # 점 표시 (수능 스타일: 검정 점)
                for pt in points:
                    if len(pt) >= 2:
                        px, py = pt[0], pt[1]
                        label = pt[2] if len(pt) > 2 else f'({px}, {py})'
                        ax.plot(px, py, 'ko', markersize=5, zorder=5)
                        ax.annotate(label, (px, py), textcoords="offset points",
                                   xytext=(5, 5), fontsize=10, color=POINT_COLOR)

                # y 범위 설정
                if y_range:
                    ax.set_ylim(y_range)

        # 공통 설정 (수직선 제외)
        if graph_type not in ['number_line', 'statistics']:
            # 눈금과 숫자 제거
            ax.set_xticks([])
            ax.set_yticks([])

            # 축 테두리 제거 (상단, 우측)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 화살표 축 스타일 설정
            ax.spines['bottom'].set_position('zero')
            ax.spines['left'].set_position('zero')
            ax.spines['bottom'].set_color('k')
            ax.spines['left'].set_color('k')

            # 축 끝에 직접 x, y 레이블 표시
            x_lim = ax.get_xlim()
            y_lim = ax.get_ylim()
            ax.annotate('$x$', xy=(x_lim[1], 0), xytext=(x_lim[1] + 0.1, 0),
                       fontsize=14, ha='left', va='center')
            ax.annotate('$y$', xy=(0, y_lim[1]), xytext=(0, y_lim[1] + 0.2),
                       fontsize=14, ha='center', va='bottom')

            # 그리드 제거
        elif graph_type == 'statistics' and plot_data.get('chart_type') not in ['pie']:
            ax.grid(True, alpha=0.3, axis='y')

        title = graph_info.get('description', '')
        if title and graph_type != 'number_line':
            # 제목에 수식 표시 지원
            ax.set_title(title, fontsize=13, pad=10)

        # 범례는 곡선에 직접 레이블로 표시하므로 사용하지 않음

        # 파일로 저장하거나 base64로 반환
        if output_path:
            # 파일로 저장
            plt.savefig(output_path, format='png', dpi=120, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            return output_path
        else:
            # base64로 변환
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            return f"data:image/png;base64,{img_base64}"

    except Exception as e:
        print(f"그래프 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


CODE_GENERATION_PROMPT = """당신은 수학/과학 교육 전문가이자 Python 프로그래머입니다.
주어진 원본 문제를 분석하고, 이 문제의 변형 문제를 생성하는 Python 함수를 작성해주세요.

## 원본 문제
{original_question}

## 요청사항
위 원본 문제를 기반으로 변형 문제를 생성하는 Python 코드를 작성해주세요.

## 중요: 반드시 아래 템플릿을 그대로 사용하세요!

def generate_variant(difficulty, variant_id):
    # 난이도별 파라미터 설정
    if difficulty == "쉬움":
        # 더 간단한 숫자 사용
        a = random.randint(1, 5)
        b = random.randint(1, 5)
    elif difficulty == "보통":
        # 원본과 비슷한 난이도
        a = random.randint(2, 10)
        b = random.randint(2, 10)
    else:  # 어려움
        # 더 복잡한 숫자
        a = random.randint(5, 20)
        b = random.randint(5, 20)

    # 정답 계산 (반드시 정확하게!)
    correct_answer = a + b  # 예시: 실제 문제에 맞게 수정

    # 오답 생성 (정답과 다른 값들)
    wrong_answers = []
    while len(wrong_answers) < 4:
        wrong = correct_answer + random.choice([-3, -2, -1, 1, 2, 3])
        if wrong != correct_answer and wrong not in wrong_answers and wrong > 0:
            wrong_answers.append(wrong)

    # 선택지 섞기
    all_answers = [correct_answer] + wrong_answers
    random.shuffle(all_answers)
    correct_idx = all_answers.index(correct_answer)

    # 선택지 번호
    choice_numbers = ["①", "②", "③", "④", "⑤"]
    choices = []
    for i, ans in enumerate(all_answers):
        choices.append({{"number": choice_numbers[i], "text": str(ans)}})

    return {{
        "variant_id": variant_id,
        "difficulty": difficulty,
        "question_text": f"${{a}} + {{b}}$의 값은?",  # LaTeX 수식 사용
        "choices": choices,
        "answer": choice_numbers[correct_idx],
        "explanation": f"[풀이]\\n사용 개념: 덧셈\\n${{a}} + {{b}} = {{correct_answer}}$\\n∴ 정답: {{choice_numbers[correct_idx]}}",
        "change_description": f"숫자를 {{a}}, {{b}}로 변경"
    }}

## 규칙
1. import 문은 작성하지 마세요 (random, math는 이미 사용 가능)
2. 함수 이름은 반드시 `generate_variant`
3. 딕셔너리 키는 정확히: variant_id, difficulty, question_text, choices, answer, explanation, change_description
4. choices는 반드시 5개, 각각 {{"number": "①", "text": "..."}} 형식
5. answer는 "①", "②", "③", "④", "⑤" 중 하나
6. 수식은 LaTeX 형식 ($..$ 또는 $$..$)
7. f-string에서 중괄호는 {{}} 로 이스케이프 (예: f"${{x}}$")
8. **explanation 작성**: "[풀이]\\n사용 개념: ...\\n$수식$\\n∴ 정답: ..." 형식

## 출력
Python 코드만 출력하세요. 마크다운 코드 블록 없이 순수 코드만!
"""


def generate_variant_code(question_data: dict) -> str:
    """원본 문제를 분석하여 변형 문제 생성 Python 코드를 생성합니다."""
    model_name = 'gemini-2.0-flash'

    # 코드 생성이므로 text 모드 사용
    generation_config = {
        "temperature": 0.5,
        "max_output_tokens": 4096,
    }

    model = genai.GenerativeModel(
        model_name,
        generation_config=generation_config
    )

    # 원본 문제 텍스트 구성
    original_text = f"문제 {question_data.get('question_number', '')}번: {question_data.get('question_text', '')}"

    if question_data.get('passage'):
        original_text += f"\n\n[지문]\n{question_data['passage']}"

    if question_data.get('choices'):
        original_text += "\n\n[선택지]"
        for choice in question_data['choices']:
            original_text += f"\n{choice['number']} {choice['text']}"

    prompt = CODE_GENERATION_PROMPT.format(original_question=original_text)

    start_time = time.time()
    response = model.generate_content(prompt)
    latency_ms = (time.time() - start_time) * 1000

    code_text = response.text.strip()

    # 사용량 추적
    tracker.track_call(
        model=model_name,
        operation="generate_variant_code",
        prompt=prompt,
        response_text=code_text,
        latency_ms=latency_ms,
        success=True
    )

    # 마크다운 코드 블록 제거
    if code_text.startswith('```'):
        lines = code_text.split('\n')
        start_idx = 1
        end_idx = len(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '```':
                end_idx = i
                break
        code_text = '\n'.join(lines[start_idx:end_idx])

    return code_text


def execute_variant_code(code: str, difficulty: str, variant_id: int) -> dict:
    """생성된 Python 코드를 실행하여 변형 문제를 생성합니다."""
    import random as random_module
    import math as math_module
    import fractions as fractions_module
    import re as re_module
    import sympy as sympy_module

    # 코드에서 import 문 제거 (이미 제공된 모듈 사용)
    # import random, import math 등을 제거
    code_lines = code.split('\n')
    filtered_lines = []
    for line in code_lines:
        stripped = line.strip()
        # import 문 건너뛰기
        if stripped.startswith('import ') or stripped.startswith('from '):
            continue
        filtered_lines.append(line)
    code = '\n'.join(filtered_lines)

    # sympy 심볼 미리 생성
    x, y, z, t, n, k = sympy_module.symbols('x y z t n k')

    # 안전한 실행 환경 구성
    safe_globals = {
        '__builtins__': {
            'range': range,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'pow': pow,
            'divmod': divmod,
            'isinstance': isinstance,
            'bool': bool,
            'any': any,
            'all': all,
            'reversed': reversed,
            'print': print,
            'True': True,
            'False': False,
            'None': None,
        },
        'random': random_module,
        'math': math_module,
        'fractions': fractions_module,
        're': re_module,
        'sympy': sympy_module,
        # sympy 심볼들 직접 제공
        'x': x, 'y': y, 'z': z, 't': t, 'n': n, 'k': k,
        # sympy 주요 함수들 직접 제공
        'Symbol': sympy_module.Symbol,
        'symbols': sympy_module.symbols,
        'sqrt': sympy_module.sqrt,
        'Rational': sympy_module.Rational,
        'simplify': sympy_module.simplify,
        'expand': sympy_module.expand,
        'factor': sympy_module.factor,
        'solve': sympy_module.solve,
        'diff': sympy_module.diff,
        'integrate': sympy_module.integrate,
        'limit': sympy_module.limit,
        'sin': sympy_module.sin,
        'cos': sympy_module.cos,
        'tan': sympy_module.tan,
        'log': sympy_module.log,
        'exp': sympy_module.exp,
        'pi': sympy_module.pi,
        'E': sympy_module.E,
        'oo': sympy_module.oo,
        'Abs': sympy_module.Abs,
    }

    local_vars = {}

    try:
        # 코드 실행
        exec(code, safe_globals, local_vars)

        # generate_variant 함수 호출
        if 'generate_variant' in local_vars:
            result = local_vars['generate_variant'](difficulty, variant_id)
            # 숫자 포맷팅 적용 (예: -0.6666... -> -0.67)
            result = format_variant_numbers(result)
            return result
        else:
            raise ValueError("generate_variant 함수를 찾을 수 없습니다")

    except Exception as e:
        return {
            "variant_id": variant_id,
            "difficulty": difficulty,
            "question_text": f"코드 실행 오류: {str(e)}",
            "choices": [],
            "answer": "",
            "explanation": f"오류 발생: {str(e)}",
            "change_description": "코드 실행 중 오류가 발생했습니다",
            "error": str(e)
        }


def generate_variants_via_code(question_data: dict, max_retries: int = 3, progress_callback=None) -> dict:
    """Python 코드 생성 방식으로 변형 문제를 생성합니다.

    코드 실행 오류 시 자동으로 코드를 재생성하여 재시도합니다.

    Args:
        question_data: 원본 문제 데이터
        max_retries: 최대 재시도 횟수
        progress_callback: 진행 상황 콜백 함수 (step, progress, message, details)
    """
    def report_progress(step, progress, message, details=None):
        """진행 상황 보고"""
        print(f"[{step}] {message}")
        if progress_callback:
            progress_callback(step, progress, message, details or {})

    difficulties = [
        ("쉬움", 3),
        ("보통", 4),
        ("어려움", 3)
    ]

    code = None
    variants = []
    last_error = None

    for retry in range(max_retries):
        report_progress('code_gen', 10 + retry * 5, f'Python 코드 생성 중... (시도 {retry + 1}/{max_retries})', {'retry': retry + 1, 'max_retries': max_retries})

        # 1. 변형 문제 생성 코드 생성
        code = generate_variant_code(question_data)
        report_progress('code_gen', 20, f'코드 생성 완료 ({len(code)} bytes)', {'code_length': len(code)})

        # 2. 코드 실행하여 변형 문제 생성
        report_progress('exec_code', 25, '변형 문제 생성 중...', {'total': 10})
        variants = []
        error_count = 0

        variant_id = 1
        total_count = sum(count for _, count in difficulties)
        for difficulty, count in difficulties:
            for i in range(count):
                variant = execute_variant_code(code, difficulty, variant_id)
                variants.append(variant)
                if variant.get('error'):
                    error_count += 1
                    last_error = variant.get('error')
                variant_id += 1
                # 각 변형 생성마다 진행률 업데이트
                progress = 25 + int((variant_id / total_count) * 15)
                report_progress('exec_code', progress, f'변형 문제 생성 중... ({variant_id}/{total_count})', {
                    'current': variant_id,
                    'total': total_count,
                    'difficulty': difficulty,
                    'errors': error_count
                })

        # 오류 비율 확인 (50% 이상 오류면 재시도)
        error_rate = error_count / len(variants) if variants else 1
        if error_rate < 0.5:
            report_progress('exec_code', 40, f'코드 실행 완료 (오류: {error_count}/{len(variants)})', {'success': True, 'error_count': error_count})
            break
        else:
            report_progress('exec_code', 35, f'오류율 {error_rate*100:.0f}% - 코드 재생성 시도...', {'error_rate': error_rate, 'retry': True})
            if retry < max_retries - 1:
                continue
            else:
                report_progress('exec_code', 35, f'최대 재시도 횟수 도달. 마지막 오류: {last_error}', {'failed': True})

    # 3. 원본 문제 풀이 생성
    report_progress('solve_original', 45, '원본 문제 풀이 생성 중...', {})
    original_solution = solve_original_question(question_data)
    report_progress('solve_original', 50, '원본 문제 풀이 완료', {})

    original = {
        "question_number": question_data.get('question_number', ''),
        "question_text": question_data.get('question_text', ''),
        "choices": question_data.get('choices', []),
        "answer": original_solution.get('answer', ''),
        "explanation": original_solution.get('explanation', ''),
        "key_concepts": original_solution.get('key_concepts', []),
    }

    result = {
        "original": original,
        "variants": variants,
        "generation_method": "code",  # 생성 방식 표시
        "generated_code": code,  # 생성된 코드도 포함
        "retry_count": retry + 1  # 몇 번째 시도에서 성공했는지
    }

    # 4. 정답 검증 - 코드 방식은 로컬 검증 먼저 수행 후 필요시 LLM 검증
    report_progress('verify', 55, '정답 검증 시작...', {'method': '로컬 검증 + LLM'})
    TARGET_VERIFIED_COUNT = 10  # 목표 검증된 문제 수
    MAX_TOTAL_ATTEMPTS = 20  # 최대 총 시도 횟수 (무한 루프 방지)

    def quick_verify(variant):
        """정답이 선택지에 포함되어 있는지 빠르게 확인"""
        answer = str(variant.get('answer', '')).strip()
        choices = variant.get('choices', [])

        if not answer or not choices:
            return None  # 확인 불가

        # 정답이 ①②③④⑤ 형태인 경우
        for choice in choices:
            choice_num = choice.get('number', '')
            if answer == choice_num:
                return True

        # 정답이 선택지 텍스트와 일치하는 경우
        for choice in choices:
            choice_text = str(choice.get('text', '')).strip()
            if answer == choice_text:
                return True

        return None  # LLM 검증 필요

    verified_variants = []
    discarded_count = 0
    llm_verified_count = 0
    total_attempts = 0
    variant_id_counter = len(variants) + 1

    # 기존 생성된 변형들 먼저 검증
    for i, variant in enumerate(variants):
        if len(verified_variants) >= TARGET_VERIFIED_COUNT:
            break

        total_attempts += 1
        progress = 55 + int((len(verified_variants) / TARGET_VERIFIED_COUNT) * 30)

        if variant.get('error'):
            report_progress('verify', progress, f'변형 {i+1}: 코드 실행 오류 - 폐기', {'variant_id': i+1, 'status': 'error'})
            discarded_count += 1
            continue

        if not variant.get('answer') or not variant.get('choices'):
            report_progress('verify', progress, f'변형 {i+1}: 정답/선택지 없음 - 폐기', {'variant_id': i+1, 'status': 'invalid'})
            discarded_count += 1
            continue

        # 1단계: 로컬 검증
        local_result = quick_verify(variant)
        if local_result is True:
            # 정답이 선택지에 있음 - 로컬 검증 통과
            variant['verification'] = {
                "is_correct": True,
                "verified_answer": variant.get('answer'),
                "verification_steps": "로컬 검증: 정답이 선택지에 포함됨",
                "confidence": "high"
            }
            verified_variants.append(variant)
            report_progress('verify', progress, f'변형 {i+1}: 로컬 검증 통과 ({len(verified_variants)}/{TARGET_VERIFIED_COUNT})', {
                'variant_id': i+1, 'status': 'local_pass', 'verified': len(verified_variants), 'target': TARGET_VERIFIED_COUNT
            })
            continue

        # 2단계: LLM 검증 (로컬 검증 불가한 경우)
        report_progress('verify', progress, f'변형 {i+1}: LLM 검증 중...', {'variant_id': i+1, 'status': 'llm_verifying'})
        llm_verified_count += 1
        verification = verify_answer(
            variant.get('question_text', ''),
            variant.get('choices', []),
            variant.get('answer', ''),
            variant.get('explanation', '')
        )
        variant['verification'] = verification

        # 검증 성공 (is_correct가 True 또는 False - null이 아님)
        if verification.get('is_correct') is not None:
            verified_variants.append(variant)
            report_progress('verify', progress, f'변형 {i+1}: LLM 검증 완료 ({len(verified_variants)}/{TARGET_VERIFIED_COUNT})', {
                'variant_id': i+1, 'status': 'llm_pass', 'verified': len(verified_variants), 'target': TARGET_VERIFIED_COUNT
            })
        else:
            report_progress('verify', progress, f'변형 {i+1}: 검증 불가 - 폐기', {'variant_id': i+1, 'status': 'llm_fail'})
            discarded_count += 1

    # 목표 개수에 미달하면 추가 생성
    while len(verified_variants) < TARGET_VERIFIED_COUNT and total_attempts < MAX_TOTAL_ATTEMPTS:
        total_attempts += 1
        needed = TARGET_VERIFIED_COUNT - len(verified_variants)
        print(f"  📝 추가 문제 생성 필요: {needed}개 (시도 {total_attempts}/{MAX_TOTAL_ATTEMPTS})")

        # 난이도 균형 맞추기
        difficulty_counts = {"쉬움": 0, "보통": 0, "어려움": 0}
        for v in verified_variants:
            d = v.get('difficulty', '보통')
            if d in difficulty_counts:
                difficulty_counts[d] += 1

        # 가장 부족한 난이도 선택
        target_counts = {"쉬움": 3, "보통": 4, "어려움": 3}
        difficulty = "보통"
        max_deficit = 0
        for d, target in target_counts.items():
            deficit = target - difficulty_counts[d]
            if deficit > max_deficit:
                max_deficit = deficit
                difficulty = d

        # 새 문제 생성
        new_variant = execute_variant_code(code, difficulty, variant_id_counter)
        variant_id_counter += 1

        if new_variant.get('error') or not new_variant.get('answer') or not new_variant.get('choices'):
            print(f"    ❌ 문제 생성 실패 - 재시도")
            discarded_count += 1
            continue

        # 로컬 검증 먼저
        local_result = quick_verify(new_variant)
        if local_result is True:
            new_variant['verification'] = {
                "is_correct": True,
                "verified_answer": new_variant.get('answer'),
                "verification_steps": "로컬 검증: 정답이 선택지에 포함됨",
                "confidence": "high"
            }
            print(f"    ✅ 로컬 검증 통과")
            verified_variants.append(new_variant)
            continue

        # LLM 검증
        llm_verified_count += 1
        verification = verify_answer(
            new_variant.get('question_text', ''),
            new_variant.get('choices', []),
            new_variant.get('answer', ''),
            new_variant.get('explanation', '')
        )
        new_variant['verification'] = verification

        if verification.get('is_correct') is not None:
            print(f"    ✅ LLM 검증 완료!")
            verified_variants.append(new_variant)
        else:
            print(f"    ❌ 검증 불가 - 폐기")
            discarded_count += 1

    result['variants'] = verified_variants
    result['discarded_count'] = discarded_count
    result['verified_count'] = len(verified_variants)
    result['llm_verified_count'] = llm_verified_count
    report_progress('verify', 90, f'검증 완료: {len(verified_variants)}개 (LLM: {llm_verified_count}회), 폐기: {discarded_count}개', {
        'verified': len(verified_variants),
        'llm_verified': llm_verified_count,
        'discarded': discarded_count
    })

    report_progress('complete', 95, '변형 문제 생성 완료!', {})
    return result


def generate_html_report(original_question: dict, variants_data: dict, output_path: str) -> str:
    """변형 문제를 HTML 리포트로 생성합니다."""

    output_folder = os.path.dirname(output_path)

    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>변형 문제 - {question_number}번</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 24px;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8em; margin-bottom: 8px; }}
        .header p {{ opacity: 0.9; }}
        .section {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .section-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #eee;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .difficulty-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .difficulty-easy {{ background: #d4edda; color: #155724; }}
        .difficulty-medium {{ background: #fff3cd; color: #856404; }}
        .difficulty-hard {{ background: #f8d7da; color: #721c24; }}
        .original-badge {{ background: #007bff; color: white; }}
        .question-card {{
            background: #fafafa;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .question-card.original {{
            background: #e3f2fd;
            border-color: #90caf9;
        }}
        .question-text {{
            font-size: 1.05em;
            margin-bottom: 16px;
            line-height: 1.8;
        }}
        .choices {{
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: flex-start;
        }}
        .choice {{
            padding: 8px 12px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            display: flex;
            gap: 6px;
            flex: 0 0 auto;
        }}
        .choice-number {{ font-weight: bold; color: #1976d2; }}
        .answer-section {{
            margin-top: 16px;
            padding: 16px;
            background: #e8f5e9;
            border-radius: 8px;
            border-left: 4px solid #4caf50;
        }}
        .answer-section h4 {{ color: #2e7d32; margin-bottom: 8px; }}
        .answer-section .explanation {{
            margin-top: 12px;
            padding: 12px;
            background: white;
            border-radius: 6px;
            line-height: 1.8;
            white-space: pre-wrap;
        }}
        .verification {{
            margin-top: 12px;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        .verification.verified {{ background: #e8f5e9; border: 1px solid #a5d6a7; }}
        .verification.unverified {{ background: #ffebee; border: 1px solid #ef9a9a; }}
        .verification.unknown {{ background: #fffde7; border: 1px solid #fff59d; }}
        .verification-header {{
            font-weight: bold;
            font-size: 1em;
            margin-bottom: 8px;
            color: #333;
        }}
        .verification.verified .verification-header {{ color: #2e7d32; }}
        .verification.unverified .verification-header {{ color: #c62828; }}
        .key-formula {{
            background: #f5f5f5;
            padding: 8px 12px;
            border-radius: 4px;
            margin: 8px 0;
            font-style: italic;
            border-left: 3px solid #1976d2;
        }}
        .verification-steps {{
            margin-top: 10px;
            padding: 10px;
            background: rgba(255,255,255,0.7);
            border-radius: 4px;
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        .detailed-solution {{
            margin-top: 10px;
            padding: 12px;
            background: rgba(255,255,255,0.9);
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            line-height: 1.8;
            white-space: pre-wrap;
        }}
        .graph-container {{
            margin-top: 16px;
            text-align: center;
        }}
        .graph-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .change-description {{
            margin-top: 12px;
            padding: 12px;
            background: #fff8e1;
            border-radius: 6px;
            font-size: 0.9em;
            color: #f57c00;
        }}
        .variant-number {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: #667eea;
            color: white;
            border-radius: 50%;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 8px;
        }}
        .timestamp {{
            text-align: center;
            color: #999;
            font-size: 0.85em;
            margin-top: 24px;
        }}
        .toggle-answer {{
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            margin-top: 12px;
        }}
        .toggle-answer:hover {{ background: #5a6268; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 변형 문제 생성 결과</h1>
            <p>원본 문제 {question_number}번 기반 - 총 {total_variants}개 변형 (검증 완료)</p>
        </div>

        <!-- 원본 문제 -->
        <div class="section">
            <div class="section-title">
                <span class="difficulty-badge original-badge">원본</span>
                문제 {question_number}번
            </div>
            <div class="question-card original">
                <div class="question-text">{original_text}</div>
                {original_question_graph}
                {original_choices}
                <button class="toggle-answer" onclick="toggleAnswer('original')">정답 및 풀이 보기</button>
                <div id="answer-original" class="answer-section hidden">
                    <h4>✅ 정답: {original_answer}</h4>
                    {original_verification}
<div class="explanation">
<strong>📝 풀이 과정:</strong><br>
{original_explanation}
</div>
                    {original_graph}
                </div>
            </div>
        </div>

        <!-- 변형 문제들 -->
        {variants_html}

        <p class="timestamp">생성 시각: {timestamp}</p>
    </div>

    <script>
        function toggleAnswer(id) {{
            const el = document.getElementById('answer-' + id);
            el.classList.toggle('hidden');
        }}

        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}}
                ]
            }});
        }});
    </script>
</body>
</html>
"""

    # 원본 선택지 HTML
    original_choices_html = ""
    original_data = variants_data.get('original', {})
    if original_data.get('choices'):
        original_choices_html = '<div class="choices">'
        for choice in original_data['choices']:
            original_choices_html += f'''
                <div class="choice">
                    <span class="choice-number">{choice["number"]}</span>
                    <span>{choice["text"]}</span>
                </div>'''
        original_choices_html += '</div>'

    # 원본 검증 HTML
    original_verification_html = ""
    original_verification = original_data.get('verification', {})
    if original_verification:
        is_correct = original_verification.get('is_correct')
        verification_steps = original_verification.get('verification_steps', '')
        detailed_solution = original_verification.get('detailed_solution', '')
        key_formula = original_verification.get('key_formula', '')
        confidence = original_verification.get('confidence', '')
        confidence_emoji = {"high": "🟢 높음", "medium": "🟡 보통", "low": "🔴 낮음"}.get(confidence, "")

        if is_correct is True:
            original_verification_html = f'''<div class="verification verified">
                <div class="verification-header">✅ 검증됨: 정답이 확인되었습니다 {f"(신뢰도: {confidence_emoji})" if confidence_emoji else ""}</div>
                {f'<div class="key-formula">📌 핵심 개념: {key_formula}</div>' if key_formula else ''}
                {f'<div class="verification-steps"><strong>검증 과정:</strong> {verification_steps}</div>' if verification_steps else ''}
                {f'<div class="detailed-solution"><strong>상세 풀이:</strong><br>{detailed_solution.replace(chr(10), "<br>")}</div>' if detailed_solution else ''}
            </div>'''
        elif is_correct is False:
            verified_answer = original_verification.get('verified_answer', '')
            original_verification_html = f'''<div class="verification unverified">
                <div class="verification-header">⚠️ 검증 결과: 정답이 {verified_answer}일 수 있습니다 {f"(신뢰도: {confidence_emoji})" if confidence_emoji else ""}</div>
                {f'<div class="key-formula">📌 핵심 개념: {key_formula}</div>' if key_formula else ''}
                {f'<div class="verification-steps"><strong>검증 과정:</strong> {verification_steps}</div>' if verification_steps else ''}
                {f'<div class="detailed-solution"><strong>상세 풀이:</strong><br>{detailed_solution.replace(chr(10), "<br>")}</div>' if detailed_solution else ''}
            </div>'''
        else:
            original_verification_html = '<div class="verification unknown">❓ 검증 불가</div>'

    # 원본 그래프 HTML (문제 영역 + 풀이 영역 분리)
    original_graph_html = ""
    original_question_graph_html = ""
    original_graph_info = original_data.get('graph_info', {})
    # graph_info가 딕셔너리인지 확인
    if isinstance(original_graph_info, dict) and original_graph_info.get('type') and original_graph_info.get('type') != 'none':
        graph_base64 = generate_graph(original_graph_info, None, 'original')
        if graph_base64:
            graph_html_content = f'''
            <div class="graph-container">
                <p><strong>📊 {original_graph_info.get('description', '시각화')}:</strong></p>
                <img src="{graph_base64}" alt="그래프">
            </div>
            '''
            # show_in_question이 true면 문제 영역에도 표시
            if original_graph_info.get('show_in_question', True):
                original_question_graph_html = graph_html_content
            # 풀이 영역에도 항상 표시
            original_graph_html = graph_html_content

    # 변형 문제 HTML
    variants_html = ""
    difficulty_groups = {"쉬움": [], "보통": [], "어려움": []}

    for variant in variants_data.get('variants', []):
        difficulty = variant.get('difficulty', '보통')
        if difficulty in difficulty_groups:
            difficulty_groups[difficulty].append(variant)

    for difficulty, variants in difficulty_groups.items():
        if not variants:
            continue

        difficulty_class = {
            "쉬움": "easy",
            "보통": "medium",
            "어려움": "hard"
        }.get(difficulty, "medium")

        difficulty_emoji = {"쉬움": "🟢", "보통": "🟡", "어려움": "🔴"}.get(difficulty, "🟡")

        variants_html += f'''
        <div class="section">
            <div class="section-title">
                <span class="difficulty-badge difficulty-{difficulty_class}">{difficulty_emoji} {difficulty}</span>
                {len(variants)}개 문제
            </div>
        '''

        for variant in variants:
            vid = variant.get('variant_id', 0)
            choices_html = ""
            if variant.get('choices'):
                choices_html = '<div class="choices">'
                for choice in variant['choices']:
                    choices_html += f'''
                        <div class="choice">
                            <span class="choice-number">{choice["number"]}</span>
                            <span>{choice["text"]}</span>
                        </div>'''
                choices_html += '</div>'

            change_desc = ""
            if variant.get('change_description'):
                change_desc = f'<div class="change-description">💡 변경사항: {variant["change_description"]}</div>'

            # 검증 HTML (상세 정보 포함)
            verification_html = ""
            verification = variant.get('verification', {})
            if isinstance(verification, dict) and verification:
                is_correct = verification.get('is_correct')
                verification_steps = verification.get('verification_steps', '')
                detailed_solution = verification.get('detailed_solution', '')
                key_formula = verification.get('key_formula', '')
                confidence = verification.get('confidence', '')

                # 신뢰도 이모지
                confidence_emoji = ""
                if confidence == 'high':
                    confidence_emoji = "🟢 높음"
                elif confidence == 'medium':
                    confidence_emoji = "🟡 중간"
                elif confidence == 'low':
                    confidence_emoji = "🔴 낮음"

                if is_correct is True:
                    verification_html = f'''<div class="verification verified">
                        <div class="verification-header">✅ 검증됨: 정답이 확인되었습니다 {f"(신뢰도: {confidence_emoji})" if confidence_emoji else ""}</div>
                        {f'<div class="key-formula">📌 핵심 개념: {key_formula}</div>' if key_formula else ''}
                        {f'<div class="verification-steps"><strong>검증 과정:</strong> {verification_steps}</div>' if verification_steps else ''}
                        {f'<div class="detailed-solution"><strong>상세 풀이:</strong><br>{detailed_solution.replace(chr(10), "<br>")}</div>' if detailed_solution else ''}
                    </div>'''
                elif is_correct is False:
                    verified_answer = verification.get('verified_answer', '')
                    verification_html = f'''<div class="verification unverified">
                        <div class="verification-header">⚠️ 정답 확인 필요 (검증 결과: {verified_answer}) {f"(신뢰도: {confidence_emoji})" if confidence_emoji else ""}</div>
                        {f'<div class="key-formula">📌 핵심 개념: {key_formula}</div>' if key_formula else ''}
                        {f'<div class="verification-steps"><strong>검증 과정:</strong> {verification_steps}</div>' if verification_steps else ''}
                        {f'<div class="detailed-solution"><strong>상세 풀이:</strong><br>{detailed_solution.replace(chr(10), "<br>")}</div>' if detailed_solution else ''}
                    </div>'''
                else:
                    verification_html = '<div class="verification unknown">❓ 검증 불가</div>'

            # 그래프 HTML (문제 영역 + 풀이 영역 분리)
            graph_html = ""
            question_graph_html = ""
            graph_info = variant.get('graph_info', {})
            # graph_info가 딕셔너리인지 확인
            if isinstance(graph_info, dict) and graph_info.get('type') and graph_info.get('type') != 'none':
                graph_base64 = generate_graph(graph_info, None, str(vid))
                if graph_base64:
                    graph_desc = graph_info.get('description', '시각화')
                    graph_content = f'''
                    <div class="graph-container">
                        <p><strong>📊 {graph_desc}:</strong></p>
                        <img src="{graph_base64}" alt="그래프">
                    </div>
                    '''
                    # show_in_question이 true면 문제 영역에도 표시
                    if graph_info.get('show_in_question', True):
                        question_graph_html = graph_content
                    # 풀이 영역에도 항상 표시
                    graph_html = graph_content

            variants_html += f'''
            <div class="question-card">
                <div class="question-text">
                    <span class="variant-number">{vid}</span>
                    {variant.get("question_text", "")}
                </div>
                {question_graph_html}
                {choices_html}
                {change_desc}
                <button class="toggle-answer" onclick="toggleAnswer('{vid}')">정답 및 풀이 보기</button>
                <div id="answer-{vid}" class="answer-section hidden">
                    <h4>✅ 정답: {variant.get("answer", "")}</h4>
                    {verification_html}
<div class="explanation">
<strong>📝 풀이 과정:</strong><br>
{variant.get("explanation", "")}
</div>
                    {graph_html}
                </div>
            </div>
            '''

        variants_html += '</div>'

    # HTML 생성
    html_content = html_template.format(
        question_number=original_data.get('question_number', original_question.get('question_number', '?')),
        total_variants=len(variants_data.get('variants', [])),
        original_text=original_data.get('question_text', original_question.get('question_text', '')),
        original_question_graph=original_question_graph_html,
        original_choices=original_choices_html,
        original_answer=original_data.get('answer', ''),
        original_explanation=original_data.get('explanation', ''),
        original_verification=original_verification_html,
        original_graph=original_graph_html,
        variants_html=variants_html,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path


def main(question_json: str, output_dir: str = 'variants_output'):
    """메인 실행 함수"""
    os.makedirs(output_dir, exist_ok=True)

    question_data = json.loads(question_json)

    print(f"변형 문제 생성 중... (문제 {question_data.get('question_number', '?')}번)")

    # 변형 문제 생성
    variants_data = generate_variants_via_code(question_data)

    # HTML 리포트 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    question_num = question_data.get('question_number', 'unknown')
    output_path = os.path.join(output_dir, f'variants_q{question_num}_{timestamp}.html')

    generate_html_report(question_data, variants_data, output_path)

    print(f"완료! 결과 파일: {output_path}")

    # JSON 결과도 저장
    json_path = os.path.join(output_dir, f'variants_q{question_num}_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(variants_data, f, ensure_ascii=False, indent=2)

    return {
        'html_path': output_path,
        'json_path': json_path,
        'variants_data': variants_data
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        question_json = sys.argv[1]
        result = main(question_json)
        print(json.dumps(result, ensure_ascii=False))
