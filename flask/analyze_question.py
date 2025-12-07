# analyze_question.py
"""
문항 시각화 모듈 (2단계 AI 방식)
1단계: 문제에서 어떤 도형을 그릴지 분석
2단계: 분석 결과를 바탕으로 JSXGraph 파라미터 생성
"""

import os
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Gemini API 설정
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# 1단계: 문제 분석 프롬프트 - 어떤 도형을 그릴지 결정
STEP1_ANALYZE_PROMPT = '''다음 수학 문제를 읽고, 시각화가 필요한지 판단하고 어떤 도형을 그려야 하는지 설명해주세요.

## 문제
{question_text}

## 응답 형식 (JSON)
```json
{{
  "needs_visualization": true/false,
  "reason": "시각화가 필요한/불필요한 이유",
  "figure_type": "geometry|function|piecewise|trigonometry|probability|sequence|none",
  "description": "그려야 할 도형에 대한 상세 설명 (좌표, 길이, 각도 등 모든 수치 포함)",
  "elements_description": [
    "점 A는 좌표 (0, 4)에 위치",
    "점 B는 좌표 (3, 0)에 위치",
    "점 A와 점 B를 연결하는 선분 AB",
    ...
  ]
}}
```

규칙:
- 함수, 그래프, 도형이 언급된 경우 needs_visualization: true
- 구간별 함수(piecewise function)는 반드시 시각화 (figure_type: "piecewise")
- 연속성, 미분가능성 문제도 함수 그래프 시각화 필요
- 확률 문제에서 벤 다이어그램, 확률 분포, 표 등이 필요하면 figure_type: "probability"
- 조건부확률, 사건의 관계, P(A), P(B), P(A∩B) 등이 있으면 시각화 가능
- 수열 문제에서 패턴을 점이나 선으로 표현하려면 figure_type: "sequence"
- 수열의 일반항, 점화식, 수열의 합 등도 그래프나 점으로 시각화 가능
- description에는 그려야 할 모든 요소를 자연어로 상세히 설명
- elements_description은 각 요소별로 구체적 정보 나열
- JSON만 출력
'''


# 2단계: 도형 파라미터 생성 프롬프트
STEP2_GENERATE_PROMPT = '''다음 도형 설명을 바탕으로 JSXGraph로 그릴 수 있는 파라미터를 생성해주세요.

## 도형 유형
{figure_type}

## 도형 설명
{description}

## 요소별 상세
{elements_description}

## 응답 형식 (JSON)
```json
{{
  "type": "{figure_type}",
  "title": "도형 제목",
  "elements": [
    {{"type": "point", "coords": [x, y], "name": "A"}},
    {{"type": "segment", "from": "A", "to": "B", "color": "black"}},
    {{"type": "circle", "center": [0, 0], "radius": 3}},
    {{"type": "polygon", "vertices": [[0,0], [4,0], [2,3]]}},
    {{"type": "function", "expr": "x^2", "color": "blue"}},
    {{"type": "function", "expr": "x^2", "domain": [-2, 3], "color": "blue"}},
    {{"type": "piecewise", "pieces": [
      {{"expr": "x+2", "domain": [-3, 0], "color": "blue"}},
      {{"expr": "x^2", "domain": [0, 2], "color": "red"}}
    ]}},
    {{"type": "sequence", "points": [[1, 2], [2, 4], [3, 6], [4, 8]], "name": "a_n"}},
    {{"type": "line", "coords": [[0,0], [1,1]]}},
    {{"type": "text", "coords": [1, 1], "content": "라벨"}},
    {{"type": "arc", "center": [0,0], "radius": 1, "startAngle": 0, "endAngle": 1.57}},
    {{"type": "angle", "points": ["A", "B", "C"], "radius": 0.5}}
  ]
}}
```

규칙:
- 점(point)은 반드시 다른 요소보다 먼저 정의
- segment의 from/to는 정의된 point의 name 사용
- 좌표는 [-6, 6] 범위 내로 조정
- 함수 표현식은 JavaScript 문법 (^는 ** 대신 ^로)
- 구간별 함수는 piecewise 타입 사용, 각 piece에 expr과 domain 필수
- domain은 [시작, 끝] 형식으로 함수가 정의되는 x 범위
- 수열(sequence)은 점들의 배열로 표현, points는 [[n, a_n], ...] 형식
- 색상은 기본 black, 강조는 blue/red
- JSON만 출력
'''


# figure_description 기반 프롬프트 (기존 유지)
FIGURE_DESC_PROMPT = '''다음 도형 설명을 바탕으로 시각화해주세요.

## 도형 설명
{figure_description}

## 응답 형식 (JSON)
```json
{{
  "type": "geometry|function|trigonometry",
  "title": "도형 제목",
  "elements": [
    {{"type": "point", "coords": [x, y], "name": "A"}},
    {{"type": "segment", "from": "A", "to": "B", "color": "black"}},
    {{"type": "circle", "center": [0, 0], "radius": 3}},
    {{"type": "polygon", "vertices": [[0,0], [4,0], [2,3]]}},
    {{"type": "function", "expr": "x^2", "color": "blue"}},
    {{"type": "line", "coords": [[0,0], [1,1]]}},
    {{"type": "text", "coords": [1, 1], "content": "라벨"}}
  ]
}}
```

규칙:
- 설명에 있는 도형 정보를 정확히 반영
- 좌표축, 그리드는 표시하지 않음
- 색상은 검정(black) 기본
- JSON만 출력
'''


def analyze_question(question_data: dict, progress_callback=None) -> dict:
    """문항을 시각화합니다 (2단계 AI 방식).

    Args:
        question_data: 문제 데이터 (question_text, figure_description 등)
        progress_callback: 진행 상황 콜백 (step, progress, message, details)

    Returns:
        시각화 결과 딕셔너리
    """
    def report_progress(step, progress, message, details=None):
        print(f"[{step}] {message}")
        if progress_callback:
            progress_callback(step, progress, message, details or {})

    report_progress('start', 0, '시각화 시작...', {})

    question_text = question_data.get('question_text', '')
    figure_description = question_data.get('figure_description', '')

    start_time = time.time()
    analysis_result = {}

    try:
        # 1. question_text 기반 2단계 도형 생성
        report_progress('step1', 20, '[1단계] 도형 분석 중...', {})
        step1_result = analyze_figure_needs(question_text)

        if step1_result and step1_result.get('needs_visualization'):
            report_progress('step2', 50, '[2단계] 도형 파라미터 생성 중...', {})
            figure_data = generate_figure_params(step1_result)

            if figure_data and figure_data.get('elements'):
                # 분석 과정도 함께 저장
                analysis_result['step1_analysis'] = step1_result
                analysis_result['step0_figure'] = figure_data

        # 2. figure_description 기반 도형 생성 (기존 방식)
        if figure_description:
            report_progress('figure_desc', 75, '도형 생성 중 (figure_description)...', {})
            figure_desc_data = generate_figure_from_description(figure_description)
            if figure_desc_data and figure_desc_data.get('elements'):
                analysis_result['step0_figure_desc'] = figure_desc_data

        latency_ms = (time.time() - start_time) * 1000
        report_progress('complete', 100, '시각화 완료!', {})

        return {
            'success': True,
            'analysis': analysis_result,
            'question_number': question_data.get('question_number', ''),
            'latency_ms': latency_ms
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        report_progress('error', 0, f'시각화 오류: {str(e)}', {'error': str(e)})
        return {
            'success': False,
            'error': str(e)
        }


def analyze_figure_needs(question_text: str) -> dict:
    """1단계: 문제에서 어떤 도형을 그릴지 분석합니다."""
    if not question_text:
        return {}

    try:
        prompt = STEP1_ANALYZE_PROMPT.format(question_text=question_text)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        text = response.text.strip()

        # 마크다운 코드블록 제거
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = 1
            end_idx = -1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[start_idx:end_idx])

        # JSON 추출
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            text = json_match.group()

        result = json.loads(text, strict=False)

        return result

    except Exception as e:
        return {}


def generate_figure_params(step1_result: dict) -> dict:
    """2단계: 분석 결과를 바탕으로 JSXGraph 파라미터를 생성합니다."""
    if not step1_result:
        return {}

    try:
        figure_type = step1_result.get('figure_type', 'geometry')
        description = step1_result.get('description', '')
        elements_desc = step1_result.get('elements_description', [])

        # elements_description을 문자열로 변환
        if isinstance(elements_desc, list):
            elements_str = '\n'.join(f"- {item}" for item in elements_desc)
        else:
            elements_str = str(elements_desc)

        prompt = STEP2_GENERATE_PROMPT.format(
            figure_type=figure_type,
            description=description,
            elements_description=elements_str
        )

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        text = response.text.strip()

        # 마크다운 코드블록 제거
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = 1
            end_idx = -1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[start_idx:end_idx])

        # JSON 추출
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            text = json_match.group()

        result = json.loads(text, strict=False)

        if not result.get('elements'):
            return {}

        return result

    except Exception as e:
        return {}


def generate_figure_from_description(figure_description: str) -> dict:
    """원본 figure_description에서 도형을 생성합니다."""
    if not figure_description:
        return {}

    try:
        prompt = FIGURE_DESC_PROMPT.format(figure_description=figure_description)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        text = response.text.strip()

        # 마크다운 코드블록 제거
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = 1
            end_idx = -1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[start_idx:end_idx])

        # JSON 추출
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            text = json_match.group()

        if text.strip() == '{}':
            return {}

        result = json.loads(text, strict=False)

        if not result.get('elements'):
            return {}

        return result

    except Exception as e:
        return {}


def generate_jsxgraph_code(elements: list, board_id: str, show_axis: bool = False) -> str:
    """파라미터 기반으로 JSXGraph JavaScript 코드를 생성합니다."""
    if not elements:
        return ""

    def expr_to_js(expr: str) -> str:
        """수학 수식을 JavaScript 표현식으로 변환"""
        expr = str(expr)
        expr = expr.replace('^', '**')
        expr = expr.replace('sin', 'Math.sin')
        expr = expr.replace('cos', 'Math.cos')
        expr = expr.replace('tan', 'Math.tan')
        expr = expr.replace('sqrt', 'Math.sqrt')
        expr = expr.replace('abs', 'Math.abs')
        expr = expr.replace('log', 'Math.log')
        expr = expr.replace('exp', 'Math.exp')
        expr = expr.replace('pi', 'Math.PI')
        expr = expr.replace('PI', 'Math.PI')
        return expr

    # 좌표축, 그리드, 레이블 모두 제거
    lines = []
    lines.append(f"var board = JXG.JSXGraph.initBoard('{board_id}', {{")
    lines.append("    boundingbox: [-6, 6, 6, -6],")
    lines.append("    axis: false,")
    lines.append("    grid: false,")
    lines.append("    showCopyright: false,")
    lines.append("    showNavigation: false")
    lines.append("});")
    lines.append("")

    named_points = {}
    point_counter = 0

    for elem in elements:
        elem_type = elem.get('type', '')

        if elem_type == 'function':
            expr = elem.get('expr', 'x')
            color = elem.get('color', '#1a1a1a')
            domain = elem.get('domain')  # [min, max] 형식
            label = elem.get('label', f'y = {expr}')
            js_expr = expr_to_js(expr)
            if domain and len(domain) == 2:
                lines.append(f"board.create('functiongraph', [function(x) {{ return {js_expr}; }}, {domain[0]}, {domain[1]}], {{strokeColor: '{color}', strokeWidth: 1}});")
                label_x = (domain[0] + domain[1]) / 2
                lines.append(f"board.create('text', [{label_x}, (function(x) {{ return {js_expr}; }})({label_x}) + 0.5, '{label}'], {{fontSize: 12, color: '{color}', useMathJax: true}});")
            else:
                lines.append(f"board.create('functiongraph', [function(x) {{ return {js_expr}; }}], {{strokeColor: '{color}', strokeWidth: 1}});")
                lines.append(f"board.create('text', [2, (function(x) {{ return {js_expr}; }})(2) + 0.5, '{label}'], {{fontSize: 12, color: '{color}', useMathJax: true}});")

        elif elem_type == 'piecewise':
            pieces = elem.get('pieces', [])
            colors = ['#1a1a1a', '#cc0000', '#006600', '#660099', '#cc6600']
            for i, piece in enumerate(pieces):
                piece_expr = piece.get('expr', 'x')
                piece_domain = piece.get('domain', [-6, 6])
                piece_color = piece.get('color', colors[i % len(colors)])
                piece_label = piece.get('label', f'y = {piece_expr}')
                js_piece_expr = expr_to_js(piece_expr)
                if len(piece_domain) == 2:
                    lines.append(f"board.create('functiongraph', [function(x) {{ return {js_piece_expr}; }}, {piece_domain[0]}, {piece_domain[1]}], {{strokeColor: '{piece_color}', strokeWidth: 1}});")
                    label_x = (piece_domain[0] + piece_domain[1]) / 2
                    lines.append(f"board.create('text', [{label_x}, (function(x) {{ return {js_piece_expr}; }})({label_x}) + 0.5, '{piece_label}'], {{fontSize: 12, color: '{piece_color}', useMathJax: true}});")

        elif elem_type == 'point':
            coords = elem.get('coords', [0, 0])
            name = elem.get('name', '')
            color = elem.get('color', 'black')
            var_name = f"p_{name}" if name else f"p_{point_counter}"
            point_counter += 1

            if name:
                named_points[name] = var_name
                if show_axis:
                    lines.append(f"var {var_name} = board.create('point', [{coords[0]}, {coords[1]}], {{name: '{name}', size: 3, color: '{color}'}});")
                else:
                    lines.append(f"var {var_name} = board.create('point', [{coords[0]}, {coords[1]}], {{name: '{name}', size: 0, color: '{color}', label: {{offset: [10, 10], fontSize: 14}}}});")
            else:
                if show_axis:
                    lines.append(f"var {var_name} = board.create('point', [{coords[0]}, {coords[1]}], {{size: 3, color: '{color}'}});")
                else:
                    lines.append(f"var {var_name} = board.create('point', [{coords[0]}, {coords[1]}], {{size: 0, color: '{color}', visible: false}});")

        elif elem_type == 'segment':
            color = elem.get('color', '#1a1a1a')
            if 'from' in elem and 'to' in elem:
                from_name = elem['from']
                to_name = elem['to']
                if isinstance(from_name, list):
                    from_var = f"seg_p{point_counter}"
                    point_counter += 1
                    lines.append(f"var {from_var} = board.create('point', [{from_name[0]}, {from_name[1]}], {{visible: false}});")
                else:
                    from_var = named_points.get(from_name, f"[{from_name}]")
                if isinstance(to_name, list):
                    to_var = f"seg_p{point_counter}"
                    point_counter += 1
                    lines.append(f"var {to_var} = board.create('point', [{to_name[0]}, {to_name[1]}], {{visible: false}});")
                else:
                    to_var = named_points.get(to_name, f"[{to_name}]")
                lines.append(f"board.create('segment', [{from_var}, {to_var}], {{strokeColor: '{color}', strokeWidth: 1}});")
            elif 'coords' in elem:
                coords = elem['coords']
                p1_var = f"seg_p{point_counter}"
                p2_var = f"seg_p{point_counter + 1}"
                point_counter += 2
                lines.append(f"var {p1_var} = board.create('point', [{coords[0][0]}, {coords[0][1]}], {{visible: false}});")
                lines.append(f"var {p2_var} = board.create('point', [{coords[1][0]}, {coords[1][1]}], {{visible: false}});")
                lines.append(f"board.create('segment', [{p1_var}, {p2_var}], {{strokeColor: '{color}', strokeWidth: 1}});")

        elif elem_type == 'line':
            color = elem.get('color', '#1a1a1a')
            if 'from' in elem and 'to' in elem:
                from_name = elem['from']
                to_name = elem['to']
                if isinstance(from_name, list):
                    from_var = f"line_p{point_counter}"
                    point_counter += 1
                    lines.append(f"var {from_var} = board.create('point', [{from_name[0]}, {from_name[1]}], {{visible: false}});")
                else:
                    from_var = named_points.get(from_name, f"[{from_name}]")
                if isinstance(to_name, list):
                    to_var = f"line_p{point_counter}"
                    point_counter += 1
                    lines.append(f"var {to_var} = board.create('point', [{to_name[0]}, {to_name[1]}], {{visible: false}});")
                else:
                    to_var = named_points.get(to_name, f"[{to_name}]")
                lines.append(f"board.create('line', [{from_var}, {to_var}], {{strokeColor: '{color}', strokeWidth: 1}});")
            elif 'coords' in elem:
                coords = elem['coords']
                p1_var = f"line_p{point_counter}"
                p2_var = f"line_p{point_counter + 1}"
                point_counter += 2
                lines.append(f"var {p1_var} = board.create('point', [{coords[0][0]}, {coords[0][1]}], {{visible: false}});")
                lines.append(f"var {p2_var} = board.create('point', [{coords[1][0]}, {coords[1][1]}], {{visible: false}});")
                lines.append(f"board.create('line', [{p1_var}, {p2_var}], {{strokeColor: '{color}', strokeWidth: 1}});")

        elif elem_type == 'circle':
            color = elem.get('color', '#1a1a1a')
            radius = elem.get('radius', 1)
            center = elem.get('center', [0, 0])

            if isinstance(center, str):
                center_var = named_points.get(center, f"[0, 0]")
            else:
                center_var = f"circle_c{point_counter}"
                point_counter += 1
                lines.append(f"var {center_var} = board.create('point', [{center[0]}, {center[1]}], {{visible: false}});")

            lines.append(f"board.create('circle', [{center_var}, {radius}], {{strokeColor: '{color}', strokeWidth: 1}});")

        elif elem_type == 'polygon':
            vertices = elem.get('vertices', [])
            color = elem.get('color', 'rgba(200,200,200,0.3)')
            stroke_color = elem.get('strokeColor', '#1a1a1a')

            vertex_vars = []
            for i, v in enumerate(vertices):
                v_var = f"poly_v{point_counter}"
                point_counter += 1
                lines.append(f"var {v_var} = board.create('point', [{v[0]}, {v[1]}], {{visible: false}});")
                vertex_vars.append(v_var)

            vertices_str = ", ".join(vertex_vars)
            lines.append(f"board.create('polygon', [{vertices_str}], {{fillColor: '{color}', fillOpacity: 0.3, borders: {{strokeColor: '{stroke_color}', strokeWidth: 1}}}});")

        elif elem_type == 'text':
            coords = elem.get('coords', [0, 0])
            content = elem.get('content', '')
            lines.append(f"board.create('text', [{coords[0]}, {coords[1]}, '{content}'], {{fontSize: 14}});")

        elif elem_type == 'sequence':
            # 수열 시각화: 점들의 배열로 표현
            points = elem.get('points', [])
            name = elem.get('name', 'a_n')
            color = elem.get('color', '#1a1a1a')
            for i, pt in enumerate(points):
                if len(pt) >= 2:
                    n_val, a_val = pt[0], pt[1]
                    pt_var = f"seq_p{point_counter}"
                    point_counter += 1
                    lines.append(f"var {pt_var} = board.create('point', [{n_val}, {a_val}], {{size: 3, color: '{color}', name: ''}});")
            # 수열 이름 레이블
            if points:
                last_pt = points[-1]
                lines.append(f"board.create('text', [{last_pt[0] + 0.5}, {last_pt[1]}, '{name}'], {{fontSize: 12, color: '{color}'}});")

        elif elem_type == 'arc':
            center = elem.get('center', [0, 0])
            radius = elem.get('radius', 1)
            start_angle = elem.get('startAngle', 0)
            end_angle = elem.get('endAngle', 3.14)
            color = elem.get('color', 'blue')

            center_var = f"arc_c{point_counter}"
            point_counter += 1
            lines.append(f"var {center_var} = board.create('point', [{center[0]}, {center[1]}], {{visible: false}});")
            lines.append(f"board.create('arc', [{center_var}, [{center[0] + radius}, {center[1]}], [{center[0] + radius * 0.7071}, {center[1] + radius * 0.7071}]], {{strokeColor: '{color}', strokeWidth: 2}});")

    return "\n".join(lines)


def clean_text_for_html(text: str) -> str:
    """HTML 출력용 텍스트 정리"""
    if not text:
        return ""
    text = str(text).strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    elif text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    return text


def generate_analysis_html(question_data: dict, analysis_data: dict) -> str:
    """시각화 결과를 HTML로 렌더링합니다."""

    analysis = analysis_data.get('analysis', {})

    # 도형 데이터
    step0_figure = analysis.get('step0_figure', {})
    step0_figure_desc = analysis.get('step0_figure_desc', {})
    figure_html = ""
    figure_js = ""

    type_labels = {
        'function': '함수 그래프',
        'geometry': '기하/도형',
        'trigonometry': '삼각함수',
        'venn': '벤다이어그램'
    }

    has_figure = step0_figure and step0_figure.get('elements')
    has_figure_desc = step0_figure_desc and step0_figure_desc.get('elements')

    if has_figure or has_figure_desc:
        figure_html = '<div class="figure-grid">'

        # 1. question_text 기반 도형 (2단계 방식)
        if has_figure:
            fig_id = "figure_box_qt"
            fig_type = step0_figure.get('type', 'geometry')
            fig_title = step0_figure.get('title', '문제 도형')

            figure_html += f'''
            <div class="figure-card">
                <div class="figure-source">📝 2단계 AI 분석 결과</div>
                <div class="figure-container">
                    <span class="figure-type {fig_type}">{type_labels.get(fig_type, fig_type)}</span>
                    <div class="figure-title">{clean_text_for_html(fig_title)}</div>
                    <div id="{fig_id}" class="jsxgraph-box"></div>
                </div>
            </div>
            '''

            elements = step0_figure.get('elements', [])
            if elements:
                js_code = generate_jsxgraph_code(elements, fig_id)
                figure_js += f'''
                try {{
                    {js_code}
                }} catch(e) {{
                    console.error('Figure error:', e);
                    document.getElementById('{fig_id}').innerHTML = '<p style="color:#c62828; padding:20px;">도형 렌더링 오류: ' + e.message + '</p>';
                }}
                '''

        # 2. figure_description 기반 도형
        if has_figure_desc:
            fig_id_desc = "figure_box_fd"
            fig_type_desc = step0_figure_desc.get('type', 'geometry')
            fig_title_desc = step0_figure_desc.get('title', '문제 도형')

            figure_html += f'''
            <div class="figure-card">
                <div class="figure-source">📋 figure_description 기반</div>
                <div class="figure-container">
                    <span class="figure-type {fig_type_desc}">{type_labels.get(fig_type_desc, fig_type_desc)}</span>
                    <div class="figure-title">{clean_text_for_html(fig_title_desc)}</div>
                    <div id="{fig_id_desc}" class="jsxgraph-box"></div>
                </div>
            </div>
            '''

            elements_desc = step0_figure_desc.get('elements', [])
            if elements_desc:
                js_code_desc = generate_jsxgraph_code(elements_desc, fig_id_desc, show_axis=False)
                figure_js += f'''
                try {{
                    {js_code_desc}
                }} catch(e) {{
                    console.error('Figure (figure_description) error:', e);
                    document.getElementById('{fig_id_desc}').innerHTML = '<p style="color:#c62828; padding:20px;">도형 렌더링 오류: ' + e.message + '</p>';
                }}
                '''

        figure_html += '</div>'

    # 도형이 없는 경우 메시지
    if not figure_html:
        figure_html = '<p style="color: #666; text-align: center; padding: 40px;">이 문제에는 시각화할 도형이 없습니다.</p>'

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>문항 시각화 - {question_data.get('question_number', '')}번</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/jsxgraph@1.8.0/distrib/jsxgraph.css">
    <script src="https://cdn.jsdelivr.net/npm/jsxgraph@1.8.0/distrib/jsxgraphcore.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #87CEEB 0%, #5DADE2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 1.5rem;
            color: #333;
            margin-bottom: 8px;
        }}
        .original-question {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            border-left: 4px solid #3498DB;
        }}
        .section {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .section-title {{
            font-size: 1.2rem;
            font-weight: 700;
            color: #3498DB;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #eee;
        }}
        .analysis-card {{
            background: #f8f9fa;
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .analysis-header {{
            background: #e3f2fd;
            padding: 12px 16px;
            font-weight: 600;
            color: #1976d2;
        }}
        .analysis-content {{
            padding: 16px;
        }}
        .analysis-item {{
            margin-bottom: 12px;
            line-height: 1.6;
        }}
        .analysis-item ul {{
            margin-top: 8px;
            padding-left: 20px;
        }}
        .analysis-item li {{
            margin-bottom: 4px;
        }}
        .figure-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        .figure-card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .figure-source {{
            background: #f0f4f8;
            padding: 10px 16px;
            font-size: 0.9rem;
            font-weight: 600;
            color: #555;
            border-bottom: 1px solid #e0e0e0;
        }}
        .figure-container {{
            background: #fafafa;
            padding: 20px;
        }}
        .figure-title {{
            font-weight: 600;
            font-size: 1.1rem;
            color: #333;
            margin-bottom: 12px;
        }}
        .jsxgraph-box {{
            width: 100%;
            height: 350px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
        }}
        .figure-type {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-bottom: 8px;
        }}
        .figure-type.function {{ background: #e3f2fd; color: #1976d2; }}
        .figure-type.geometry {{ background: #f3e5f5; color: #7b1fa2; }}
        .figure-type.trigonometry {{ background: #e8f5e9; color: #388e3c; }}
        .figure-type.venn {{ background: #fff3e0; color: #f57c00; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖼️ 문항 시각화 - {question_data.get('question_number', '')}번</h1>
            <div class="original-question">
                <strong>원본 문제:</strong><br>
                {question_data.get('question_text', '')}
            </div>
        </div>

        <div class="section">
            <div class="section-title">📊 도형/그래프</div>
            {figure_html}
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}}
                ],
                throwOnError: false
            }});

            {figure_js if figure_js else '// 도형 없음'}
        }});
    </script>
</body>
</html>'''

    return html


if __name__ == '__main__':
    # 테스트
    test_question = {
        "question_number": "1",
        "question_text": "좌표평면 위에 세 점 A(0, 4), B(3, 0), C(-2, 0)이 있다. 삼각형 ABC의 넓이를 구하시오.",
        "figure_description": "좌표평면 위에 점 A(0, 4), B(3, 0), C(-2, 0)이 있고, 세 점을 연결한 삼각형 ABC가 있다."
    }

    result = analyze_question(test_question)
    if result['success']:
        print("시각화 성공")
        print(json.dumps(result['analysis'], ensure_ascii=False, indent=2))
    else:
        print(f"Error: {result.get('error')}")
