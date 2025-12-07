# generate_exam.py
"""
수능 스타일 문제지 HTML 생성 모듈
- 2단 레이아웃
- 흑백/그레이 색상만 사용
- 문제 풀이 여백 포함
- 페이지 번호
- 객관식 형식
- 그래프는 Function Plot (JS) 사용
"""

import re
import json
from datetime import datetime


def clean_float(text: str) -> str:
    """부동소수점 정밀도 문제 정리 (0.19999999999999998 -> 0.2)"""
    if not text:
        return ""

    # 긴 소수점 숫자 패턴 찾기 (소수점 이하 10자리 이상)
    def round_float(match):
        num_str = match.group(0)
        try:
            num = float(num_str)
            # 반올림하여 정리 (소수점 10자리로 반올림 후 불필요한 0 제거)
            rounded = round(num, 10)
            # 정수에 가까우면 정수로
            if rounded == int(rounded):
                return str(int(rounded))
            # 그렇지 않으면 불필요한 0 제거
            result = f"{rounded:.10f}".rstrip('0').rstrip('.')
            return result
        except:
            return num_str

    # 소수점 이하 10자리 이상인 숫자 패턴
    pattern = r'-?\d+\.\d{10,}'
    return re.sub(pattern, round_float, text)


def escape_html(text: str) -> str:
    """HTML 특수문자 이스케이프 (LaTeX는 유지)"""
    if not text:
        return ""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def format_math_text(text: str) -> str:
    """LaTeX 수식을 KaTeX 렌더링 가능한 형식으로 변환"""
    if not text:
        return ""

    # 먼저 부동소수점 정밀도 문제 정리
    text = clean_float(text)

    # HTML 이스케이프 (수식 외부만)
    parts = re.split(r'(\$\$[\s\S]*?\$\$|\$[^$]+?\$)', text)
    result = []
    for part in parts:
        if part.startswith('$$') and part.endswith('$$'):
            # 수식 내부도 부동소수점 정리
            result.append(clean_float(part))
        elif part.startswith('$') and part.endswith('$'):
            result.append(clean_float(part))
        else:
            result.append(escape_html(part))

    return ''.join(result)


def format_explanation(text: str) -> str:
    """해설을 단락별 HTML로 포맷팅 (단계 번호 제거)"""
    if not text:
        return ""

    # 줄바꿈으로 분리
    lines = text.split('\n')
    html_parts = []
    current_block = []
    is_title_line = []  # 제목 라인인지 여부

    for line in lines:
        line = line.strip()
        if not line:
            # 빈 줄이면 현재 블록 저장
            if current_block:
                formatted = []
                for i, c in enumerate(current_block):
                    if is_title_line[i]:
                        formatted.append(f'<strong>{format_math_text(c)}</strong>')
                    else:
                        formatted.append(format_math_text(c))
                content_html = '<br>'.join(formatted)
                html_parts.append(f'<div class="exp-block">{content_html}</div>')
                current_block = []
                is_title_line = []
            continue

        # [1단계], [2단계] 등의 패턴 제거하고 내용만 추출
        step_match = re.match(r'^\[(\d+단계)\]\s*(.*)$', line)
        if step_match:
            # 이전 블록 저장
            if current_block:
                formatted = []
                for i, c in enumerate(current_block):
                    if is_title_line[i]:
                        formatted.append(f'<strong>{format_math_text(c)}</strong>')
                    else:
                        formatted.append(format_math_text(c))
                content_html = '<br>'.join(formatted)
                html_parts.append(f'<div class="exp-block">{content_html}</div>')
                current_block = []
                is_title_line = []
            # 단계 제목 텍스트만 추가 (번호 제외)
            step_title = step_match.group(2).strip()
            if step_title:
                current_block.append(step_title)
                is_title_line.append(True)
        elif line.startswith('- '):
            # 목록 항목
            current_block.append(f'• {line[2:]}')
            is_title_line.append(False)
        elif line.startswith('**') and line.endswith('**'):
            # 강조 텍스트 (제목) - 별도 블록으로
            if current_block:
                formatted = []
                for i, c in enumerate(current_block):
                    if is_title_line[i]:
                        formatted.append(f'<strong>{format_math_text(c)}</strong>')
                    else:
                        formatted.append(format_math_text(c))
                content_html = '<br>'.join(formatted)
                html_parts.append(f'<div class="exp-block">{content_html}</div>')
                current_block = []
                is_title_line = []
            html_parts.append(f'<div class="exp-title">{format_math_text(line[2:-2])}</div>')
        else:
            current_block.append(line)
            is_title_line.append(False)

    # 마지막 블록 저장
    if current_block:
        formatted = []
        for i, c in enumerate(current_block):
            if is_title_line[i]:
                formatted.append(f'<strong>{format_math_text(c)}</strong>')
            else:
                formatted.append(format_math_text(c))
        content_html = '<br>'.join(formatted)
        html_parts.append(f'<div class="exp-block">{content_html}</div>')

    return ''.join(html_parts)


def generate_graph_html(graph_info: dict, graph_id: str) -> str:
    """그래프 정보를 Function Plot으로 렌더링할 HTML 생성"""
    if not graph_info or graph_info.get('type') == 'none':
        return ""

    graph_type = graph_info.get('type', '')
    plot_data = graph_info.get('plot_data', {})

    # graph_info를 JSON으로 변환하여 JavaScript에서 사용
    graph_json = json.dumps(graph_info, ensure_ascii=False)

    return f'''
<div class="graph-container">
    <div id="{graph_id}" class="graph-plot" data-graph='{graph_json}'></div>
</div>
'''


def generate_exam_html(questions: list, title: str = "수학 모의고사", include_answer_sheet: bool = True) -> str:
    """수능 스타일 문제지 HTML 생성"""

    today = datetime.now().strftime('%Y년 %m월 %d일')

    # 빈 문제 필터링 (question_text가 있는 문제만)
    valid_questions = [q for q in questions if q.get('question_text', '').strip()]

    # 문항별 HTML 생성
    questions_html = ""
    answers = []
    graph_count = 0

    for idx, q in enumerate(valid_questions, 1):
        q_num = idx
        q_text = format_math_text(q.get('question_text', ''))
        choices = q.get('choices', [])
        points = q.get('points', 3)

        # 지문이 있는 경우
        passage_html = ""
        if q.get('has_passage') and q.get('passage'):
            passage = format_math_text(q.get('passage'))
            passage_html = f'''
<div class="passage">
{passage}
</div>'''

        # 선택지 생성 - 한 줄로 나란히
        choices_html = ""
        answer = q.get('answer', '')
        explanation = q.get('explanation', '')
        graph_info = q.get('graph_info', {})

        if choices:
            choices_html = '<div class="choices">'
            for c in choices:
                c_num = c.get('number', '')
                c_text = format_math_text(c.get('text', ''))
                choices_html += f'<span class="choice"><span class="choice-num">{c_num}</span>{c_text}</span>'
            choices_html += '</div>'

            # 정답과 해설 저장 (graph_info 포함)
            answers.append((q_num, answer if answer else '-', explanation, graph_info))
        else:
            # 주관식
            choices_html = '<div class="answer-blank"></div>'
            answers.append((q_num, answer if answer else '-', explanation, graph_info))

        # 그림/도표 설명
        figure_html = ""
        if q.get('has_figure') and q.get('figure_description'):
            figure_html = f'''
<div class="figure-box">
[그림] {escape_html(q.get('figure_description'))}
</div>'''

        questions_html += f'''
<div class="question">
<div class="q-header">
<span class="q-num">{q_num}</span>
<span class="q-points">[{points}점]</span>
</div>
<div class="q-content">
{passage_html}
<div class="q-text">{q_text}</div>
{figure_html}
{choices_html}
</div>
<div class="work-space"></div>
</div>
'''

    # 정답 및 해설 HTML
    answer_sheet_html = ""
    if include_answer_sheet and answers:
        answer_items = ""
        for q_num, ans, explanation, graph_info in answers:
            # 단계별 해설 포맷팅
            explanation_html = format_explanation(explanation) if explanation else ""

            # 그래프 HTML 생성 (Function Plot 사용)
            graph_html = ""
            if graph_info and graph_info.get('type') != 'none':
                graph_id = f"graph-{graph_count}"
                graph_count += 1
                graph_html = generate_graph_html(graph_info, graph_id)

            answer_items += f'''
<div class="answer-item">
<div class="answer-header">
<span class="answer-num">{q_num}번</span>
<span class="answer-value">정답: {ans}</span>
</div>
{graph_html}
<div class="explanation">{explanation_html}</div>
</div>'''

        answer_sheet_html = f'''
<div class="page answer-sheet-page">
<div class="answer-sheet">
<h2>정답 및 해설</h2>
<div class="answer-list">
{answer_items}
</div>
</div>
<div class="page-number"></div>
</div>
'''

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/function-plot@1/dist/function-plot.min.js"></script>
<style>
/* 인쇄 설정 - A3 */
@media print {{
    @page {{
        size: A3 portrait;
        margin: 10mm;
    }}
    body {{
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}
    .no-print {{
        display: none !important;
    }}
    .page {{
        page-break-after: always;
        box-shadow: none !important;
        margin: 0 !important;
    }}
    .page:last-child {{
        page-break-after: avoid;
    }}
}}

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #000;
    background: #e0e0e0;
}}

/* A3 페이지 스타일 (297mm x 420mm) */
.page {{
    width: 297mm;
    min-height: 420mm;
    margin: 10mm auto;
    padding: 15mm 20mm;
    background: #fff;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    position: relative;
}}

/* 인쇄 스타일 */
@media print {{
    @page {{
        size: A3 portrait;
        margin: 15mm 20mm;
    }}

    body {{
        background: #fff;
    }}

    .page {{
        width: 100%;
        min-height: auto;
        margin: 0;
        padding: 0;
        box-shadow: none;
        page-break-after: always;
    }}

    .page:last-child {{
        page-break-after: auto;
    }}

    .print-btn {{
        display: none !important;
    }}

    .two-column {{
        column-count: 2;
        column-gap: 25px;
        column-fill: auto;
    }}

    .question {{
        break-inside: avoid;
        page-break-inside: avoid;
    }}

    .answer-sheet-page {{
        page-break-before: always;
    }}
}}

/* 헤더 */
.exam-header {{
    text-align: center;
    border-bottom: 3px double #000;
    padding-bottom: 12px;
    margin-bottom: 20px;
}}

.exam-title {{
    font-size: 28pt;
    font-weight: bold;
    letter-spacing: 3px;
    margin-bottom: 8px;
}}

.exam-info {{
    font-size: 11pt;
    color: #333;
}}

/* 2단 레이아웃 */
.two-column {{
    -webkit-column-count: 2;
    -moz-column-count: 2;
    column-count: 2;
    -webkit-column-gap: 25px;
    -moz-column-gap: 25px;
    column-gap: 25px;
    column-rule: 1px solid #ccc;
}}

/* 문항 스타일 */
.question {{
    -webkit-column-break-inside: avoid;
    break-inside: avoid;
    page-break-inside: avoid;
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px dotted #aaa;
}}

.q-header {{
    display: flex;
    align-items: center;
    margin-bottom: 8px;
}}

.q-num {{
    font-weight: bold;
    font-size: 14pt;
    margin-right: 8px;
}}

.q-points {{
    font-size: 9pt;
    color: #555;
}}

.q-content {{
    padding-left: 36px;
}}

.q-text {{
    margin-bottom: 10px;
    text-align: justify;
    word-break: keep-all;
}}

/* 지문 박스 */
.passage {{
    background: #f5f5f5;
    border-left: 3px solid #666;
    padding: 10px 12px;
    margin-bottom: 10px;
    font-size: 10pt;
}}

/* 그림 박스 */
.figure-box {{
    border: 1px solid #999;
    padding: 12px;
    margin: 10px 0;
    text-align: center;
    background: #fafafa;
    color: #666;
    font-size: 9pt;
}}

/* 선택지 - 한 줄로 나란히 */
.choices {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px 20px;
    margin-top: 10px;
    align-items: baseline;
}}

.choice {{
    display: inline-flex;
    align-items: baseline;
    font-size: 10.5pt;
    white-space: nowrap;
}}

.choice-num {{
    font-weight: bold;
    margin-right: 4px;
}}

/* 주관식 답란 */
.answer-blank {{
    border: 1px solid #000;
    height: 35px;
    margin-top: 10px;
    background: #fafafa;
}}

/* 필기 여백 - 컬럼 너비에 꽉 차게 */
.work-space {{
    width: 100%;
    height: 240px;
    margin-top: 12px;
    border: 1px dashed #bbb;
    background: repeating-linear-gradient(
        #fff,
        #fff 23px,
        #f0f0f0 23px,
        #f0f0f0 24px
    );
    border-radius: 4px;
}}

/* 페이지 번호 */
.page-number {{
    position: absolute;
    bottom: 12mm;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 11pt;
    color: #666;
}}

/* 정답 및 해설 페이지 */
.answer-sheet-page {{
    display: block;
    padding-top: 15mm;
}}

.answer-sheet {{
    width: 100%;
}}

.answer-sheet h2 {{
    text-align: center;
    font-size: 20pt;
    margin-bottom: 25px;
    padding-bottom: 12px;
    border-bottom: 2px solid #000;
}}

.answer-list {{
    -webkit-column-count: 2;
    -moz-column-count: 2;
    column-count: 2;
    -webkit-column-gap: 25px;
    -moz-column-gap: 25px;
    column-gap: 25px;
    column-rule: 1px solid #ccc;
}}

.answer-item {{
    -webkit-column-break-inside: avoid;
    break-inside: avoid;
    page-break-inside: avoid;
    margin-bottom: 15px;
    padding-bottom: 12px;
    border-bottom: 1px dotted #aaa;
}}

.answer-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}}

.answer-num {{
    font-weight: bold;
    font-size: 12pt;
    color: #333;
}}

.answer-value {{
    font-weight: bold;
    font-size: 12pt;
    color: #000;
    background: #f0f0f0;
    padding: 2px 10px;
    border-radius: 4px;
}}

.explanation {{
    font-size: 10pt;
    line-height: 1.7;
    color: #333;
    padding-left: 5px;
    word-break: keep-all;
}}

/* 해설 스타일 */
.exp-title {{
    font-weight: bold;
    font-size: 11pt;
    margin-bottom: 10px;
    color: #000;
}}

.exp-block {{
    margin-bottom: 10px;
    padding-left: 8px;
    border-left: 2px solid #ddd;
    font-size: 10pt;
    line-height: 1.8;
    color: #333;
}}

/* 그래프 스타일 */
.graph-container {{
    text-align: center;
    margin: 10px 0;
    padding: 8px;
    background: #fafafa;
    border: 1px solid #ddd;
    border-radius: 4px;
}}

.graph-plot {{
    width: 100%;
    max-width: 350px;
    height: 250px;
    margin: 0 auto;
}}

.graph-error {{
    color: #666;
    font-size: 9pt;
    font-style: italic;
    padding: 10px;
    background: #f5f5f5;
    border-radius: 4px;
}}

/* 인쇄 버튼 */
.print-btn {{
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 14px 28px;
    background: #333;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    cursor: pointer;
    z-index: 1000;
}}

.print-btn:hover {{
    background: #555;
}}

/* KaTeX 스타일 조정 */
.katex {{
    font-size: 1.05em;
}}
</style>
</head>
<body>
<button class="print-btn no-print" onclick="window.print()">인쇄하기</button>

<div class="page">
<header class="exam-header">
<h1 class="exam-title">{escape_html(title)}</h1>
<div class="exam-info">{today} | 문항 수: {len(valid_questions)}개</div>
</header>

<main class="two-column" id="questions-container">
{questions_html}
</main>

<div class="page-number">- 1 -</div>
</div>

{answer_sheet_html}

<script>
document.addEventListener("DOMContentLoaded", function() {{
    // KaTeX 렌더링
    renderMathInElement(document.body, {{
        delimiters: [
            {{left: "$$", right: "$$", display: true}},
            {{left: "$", right: "$", display: false}}
        ],
        throwOnError: false
    }});

    // Function Plot으로 그래프 렌더링
    document.querySelectorAll('.graph-plot').forEach(function(el) {{
        try {{
            const graphData = JSON.parse(el.dataset.graph);
            renderGraph(el.id, graphData);
        }} catch (e) {{
            el.innerHTML = '<div class="graph-error">[그래프 렌더링 오류]</div>';
        }}
    }});
}});

function renderGraph(elementId, graphInfo) {{
    const plotData = graphInfo.plot_data || {{}};
    const graphType = graphInfo.type || '';
    const target = '#' + elementId;

    try {{
        if (graphType === 'function') {{
            // 함수 그래프
            const xRange = plotData.x_range || [-5, 5];
            const functions = plotData.functions || [];

            const data = functions.map(f => ({{
                fn: f.expression.replace(/np\./g, 'Math.').replace(/\*\*/g, '^'),
                color: f.color || 'black'
            }}));

            if (data.length > 0) {{
                functionPlot({{
                    target: target,
                    width: 350,
                    height: 250,
                    xAxis: {{ domain: xRange }},
                    yAxis: {{ domain: [-10, 10] }},
                    grid: true,
                    data: data
                }});
            }}
        }} else if (graphType === 'coordinate') {{
            // 좌표평면에 점/선
            const points = plotData.points || [];
            const lines = plotData.lines || [];

            const data = [];

            // 선 추가
            lines.forEach(line => {{
                if (line.x && line.y && line.x.length >= 2) {{
                    data.push({{
                        points: line.x.map((x, i) => [x, line.y[i]]),
                        fnType: 'points',
                        graphType: 'polyline',
                        color: 'black'
                    }});
                }}
            }});

            // 점 추가
            points.forEach(pt => {{
                data.push({{
                    points: [[pt.x, pt.y]],
                    fnType: 'points',
                    graphType: 'scatter',
                    color: 'black'
                }});
            }});

            if (data.length > 0) {{
                functionPlot({{
                    target: target,
                    width: 350,
                    height: 250,
                    xAxis: {{ domain: [-5, 5] }},
                    yAxis: {{ domain: [-5, 5] }},
                    grid: true,
                    data: data
                }});
            }}
        }} else if (graphType === 'geometry') {{
            // 도형 - SVG로 직접 그리기
            const shapes = plotData.shapes || [];
            let svgContent = '<svg viewBox="-5 -5 10 10" style="width:100%;height:100%;background:#fff">';
            svgContent += '<line x1="-5" y1="0" x2="5" y2="0" stroke="#ccc" stroke-width="0.05"/>';
            svgContent += '<line x1="0" y1="-5" x2="0" y2="5" stroke="#ccc" stroke-width="0.05"/>';

            shapes.forEach(shape => {{
                if (shape.type === 'circle') {{
                    svgContent += `<circle cx="${{shape.cx||0}}" cy="${{-(shape.cy||0)}}" r="${{shape.r||1}}" fill="none" stroke="black" stroke-width="0.05"/>`;
                }} else if (shape.type === 'polygon') {{
                    const pts = (shape.vertices || []).map(v => `${{v[0]}},${{-v[1]}}`).join(' ');
                    svgContent += `<polygon points="${{pts}}" fill="none" stroke="black" stroke-width="0.05"/>`;
                }} else if (shape.type === 'line') {{
                    svgContent += `<line x1="${{shape.x1||0}}" y1="${{-(shape.y1||0)}}" x2="${{shape.x2||1}}" y2="${{-(shape.y2||1)}}" stroke="black" stroke-width="0.05"/>`;
                }}
            }});

            svgContent += '</svg>';
            document.getElementById(elementId).innerHTML = svgContent;
        }} else if (graphType === 'number_line') {{
            // 수직선 - SVG
            const points = plotData.points || [];
            let svgContent = '<svg viewBox="-6 -1 12 2" style="width:100%;height:60px;background:#fff">';
            svgContent += '<line x1="-5" y1="0" x2="5" y2="0" stroke="black" stroke-width="0.05"/>';

            points.forEach(pt => {{
                svgContent += `<circle cx="${{pt.x}}" cy="0" r="0.15" fill="black"/>`;
                if (pt.label) {{
                    svgContent += `<text x="${{pt.x}}" y="0.6" font-size="0.4" text-anchor="middle">${{pt.label}}</text>`;
                }}
            }});

            svgContent += '</svg>';
            document.getElementById(elementId).innerHTML = svgContent;
        }} else if (graphType === 'venn' || graphType === 'venn_diagram') {{
            // 벤다이어그램 - SVG
            const sets = plotData.sets || [];
            const values = plotData.values || [];
            let svgContent = '<svg viewBox="-3 -2.5 6 5" style="width:100%;height:100%;background:#fff">';

            // 전체집합 사각형
            svgContent += '<rect x="-2.5" y="-2" width="5" height="4" fill="none" stroke="black" stroke-width="0.03"/>';

            // 집합 원
            const colors = ['rgba(52,152,219,0.3)', 'rgba(231,76,60,0.3)', 'rgba(46,204,113,0.3)'];
            sets.forEach((s, i) => {{
                const cx = s.cx !== undefined ? s.cx : (-0.7 + i * 1.4);
                const cy = s.cy !== undefined ? s.cy : 0;
                const r = s.r || 1.2;
                svgContent += `<circle cx="${{cx}}" cy="${{-cy}}" r="${{r}}" fill="${{colors[i % 3]}}" stroke="black" stroke-width="0.03"/>`;
                if (s.label) {{
                    svgContent += `<text x="${{cx}}" y="${{-(cy + r + 0.3)}}" font-size="0.4" text-anchor="middle" font-weight="bold">${{s.label}}</text>`;
                }}
            }});

            // 값 표시
            values.forEach(v => {{
                svgContent += `<text x="${{v.x}}" y="${{-v.y}}" font-size="0.35" text-anchor="middle" font-weight="bold">${{v.value}}</text>`;
            }});

            svgContent += '</svg>';
            document.getElementById(elementId).innerHTML = svgContent;
        }} else {{
            document.getElementById(elementId).innerHTML = '<div class="graph-error">[지원하지 않는 그래프 유형]</div>';
        }}
    }} catch (e) {{
        console.error('Graph render error:', e);
        document.getElementById(elementId).innerHTML = '<div class="graph-error">[그래프 렌더링 오류]</div>';
    }}
}}
</script>
</body>
</html>
'''

    return html
