# app.py

import os
import json
import re
import shutil
from flask import Flask, request, jsonify, send_from_directory, Response, send_file
from flask_cors import CORS
import time
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
from llm_tracker import tracker
from generate_variants import generate_graph

# 유틸리티 모듈 import
from utils.json_parser import parse_gemini_json
from utils.image import crop_image_by_bbox
from utils.llm import ask_llm_to_fix_error, ask_llm_to_fix_json_error

# 라우트 모듈에서 프롬프트 함수 import
from routes.prompts import get_system_prompt, get_user_prompt, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT


# .env 파일에서 환경 변수 로드
load_dotenv()

# Gemini API 설정
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
genai.configure(api_key=GEMINI_API_KEY)

# 서버 설정 (배포 시 환경 변수로 변경)
PORT = int(os.environ.get('PORT', 4001))
SERVER_URL = os.environ.get('SERVER_URL', f'http://localhost:{PORT}')

app = Flask(__name__)
CORS(app)

# GEN_DATA_PATH: 생성 데이터 저장 경로 (환경 변수로 설정 가능)
GEN_DATA_PATH = os.path.expanduser(os.environ.get('GEN_DATA_PATH', '~/.gen-data'))
os.makedirs(GEN_DATA_PATH, exist_ok=True)

UPLOAD_FOLDER = os.path.join(GEN_DATA_PATH, 'flask_uploads')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
CONFIG_FOLDER = 'config'  # config는 프로젝트 내부에 유지
SESSIONS_FOLDER = os.path.join(GEN_DATA_PATH, 'data', 'sessions')
VARIANTS_FOLDER = os.path.join(GEN_DATA_PATH, 'variants_output')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['CONFIG_FOLDER'] = CONFIG_FOLDER
app.config['SESSIONS_FOLDER'] = SESSIONS_FOLDER
app.config['VARIANTS_FOLDER'] = VARIANTS_FOLDER
app.config['GEN_DATA_PATH'] = GEN_DATA_PATH

os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(VARIANTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_exam_image(img, system_prompt=None, user_prompt=None):
    """Gemini Vision으로 시험 문항 이미지를 분석합니다."""
    # gemini-2.5-pro 사용 (이미지 분석에 가장 정확함)
    model_name = 'gemini-2.5-pro'
    model = genai.GenerativeModel(model_name)

    # 시스템 프롬프트와 사용자 프롬프트 결합
    sys_prompt = system_prompt if system_prompt else get_system_prompt()
    usr_prompt = user_prompt if user_prompt else get_user_prompt()

    # 프롬프트 결합: 시스템 프롬프트 + 사용자 프롬프트
    combined_prompt = sys_prompt
    if usr_prompt and usr_prompt.strip():
        combined_prompt += "\n\n--- 추가 지시사항 ---\n" + usr_prompt

    start_time = time.time()
    try:
        response = model.generate_content([combined_prompt, img])
        latency_ms = (time.time() - start_time) * 1000

        # 사용량 추적
        tracker.track_call(
            model=model_name,
            operation="analyze_image",
            prompt=combined_prompt,
            response_text=response.text,
            latency_ms=latency_ms,
            success=True
        )

        return parse_gemini_json(response.text)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        tracker.track_call(
            model=model_name,
            operation="analyze_image",
            prompt=combined_prompt,
            response_text="",
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        raise


@app.route('/prompts', methods=['GET'])
def get_prompts():
    """시스템 프롬프트와 사용자 프롬프트를 반환합니다."""
    return jsonify({
        "success": True,
        "system_prompt": get_system_prompt(),
        "user_prompt": get_user_prompt(),
        "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
        "default_user_prompt": DEFAULT_USER_PROMPT
    })


@app.route('/prompts', methods=['POST'])
def save_prompts():
    """시스템 프롬프트와 사용자 프롬프트를 저장합니다."""
    data = request.get_json()

    if 'system_prompt' in data:
        save_prompt(SYSTEM_PROMPT_FILE, data['system_prompt'])

    if 'user_prompt' in data:
        save_prompt(USER_PROMPT_FILE, data['user_prompt'])

    return jsonify({
        "success": True,
        "message": "프롬프트가 저장되었습니다.",
        "system_prompt": get_system_prompt(),
        "user_prompt": get_user_prompt()
    })


@app.route('/prompts/reset', methods=['POST'])
def reset_prompts():
    """프롬프트를 기본값으로 초기화합니다."""
    data = request.get_json() or {}
    reset_type = data.get('type', 'all')  # 'system', 'user', 'all'

    if reset_type in ['system', 'all']:
        if os.path.exists(SYSTEM_PROMPT_FILE):
            os.remove(SYSTEM_PROMPT_FILE)

    if reset_type in ['user', 'all']:
        if os.path.exists(USER_PROMPT_FILE):
            os.remove(USER_PROMPT_FILE)

    return jsonify({
        "success": True,
        "message": "프롬프트가 초기화되었습니다.",
        "system_prompt": get_system_prompt(),
        "user_prompt": get_user_prompt()
    })


@app.route('/analyze', methods=['POST'])
def analyze_file():
    """이미지 파일을 업로드하고 Gemini Vision으로 바로 분석합니다."""
    if 'image_file' not in request.files:
        return jsonify({"success": False, "message": "이미지 파일이 없습니다."}), 400

    file = request.files['image_file']
    if file.filename == '':
        return jsonify({"success": False, "message": "파일 이름이 비어있습니다."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "지원하지 않는 파일 형식입니다. (png, jpg, jpeg, gif, webp만 가능)"}), 400

    # 시스템/사용자 프롬프트 받기
    system_prompt = request.form.get('system_prompt', None)
    user_prompt = request.form.get('user_prompt', None)

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['IMAGES_FOLDER'], filename)
    file.save(filepath)

    try:
        img = Image.open(filepath)
        image_url = f"{SERVER_URL}/images/{filename}"

        # Gemini Vision으로 바로 분석
        try:
            result = analyze_exam_image(img, system_prompt, user_prompt)
            print(f"Analyzed {len(result.get('questions', []))} questions")

            # 각 문항의 graph_info가 있으면 그래프 생성
            for question in result.get('questions', []):
                graph_info = question.get('graph_info')
                if graph_info and graph_info.get('type') and graph_info.get('plot_data'):
                    try:
                        q_num = question.get('question_number', 'unknown')
                        graph_filename = f"graph_q{q_num}_{uuid.uuid4().hex[:8]}.png"
                        graph_path = os.path.join(app.config['IMAGES_FOLDER'], graph_filename)

                        # 그래프 생성
                        generate_graph(graph_info, graph_path)

                        # graph_url 추가
                        question['graph_url'] = f"{SERVER_URL}/images/{graph_filename}"
                        print(f"Generated graph for question {q_num}: {graph_filename}")
                    except Exception as graph_error:
                        print(f"Graph generation error for question {q_num}: {graph_error}")
                        question['graph_error'] = str(graph_error)

        except Exception as gemini_error:
            print(f"Gemini API Error: {gemini_error}")
            import traceback
            traceback.print_exc()
            result = {"questions": [], "error": str(gemini_error)}

        return jsonify({
            "success": True,
            "filename": filename,
            "image_url": image_url,
            "message": "분석 완료",
            "data": result
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"분석 중 오류 발생: {str(e)}"}), 500


# 변형 문제 생성 관련 (VARIANTS_FOLDER는 위에서 정의됨)
# 진행 상태 저장소
variant_progress = {}

# 최대 자동 복구 시도 횟수
MAX_AUTO_RETRY = 2


def ask_llm_to_fix_error(error_message: str, error_context: str, original_data: dict) -> dict:
    """LLM에게 오류 수정을 요청합니다."""
    model_name = 'gemini-2.0-flash'
    model = genai.GenerativeModel(model_name)

    fix_prompt = f"""다음 오류가 발생했습니다. 문제 데이터를 수정하여 오류를 해결해주세요.

## 오류 메시지
{error_message}

## 오류 컨텍스트
{error_context}

## 원본 문제 데이터
{json.dumps(original_data, ensure_ascii=False, indent=2)}

## 요청사항
1. 오류의 원인을 분석하세요
2. 문제 데이터에서 오류를 일으키는 부분을 찾아 수정하세요
3. 특히 수식이나 특수문자가 문제가 될 수 있습니다
4. 수정된 데이터를 JSON 형식으로 반환하세요

## 출력 형식
```json
{{
  "analysis": "오류 원인 분석",
  "fix_description": "수정 내용 설명",
  "fixed_data": {{ ... 수정된 문제 데이터 ... }},
  "can_fix": true/false
}}
```

중요: JSON만 출력하세요.
"""

    start_time = time.time()
    try:
        response = model.generate_content(fix_prompt)
        latency_ms = (time.time() - start_time) * 1000
        text = response.text.strip()

        # 사용량 추적
        tracker.track_call(
            model=model_name,
            operation="fix_error",
            prompt=fix_prompt,
            response_text=text,
            latency_ms=latency_ms,
            success=True
        )

        # JSON 파싱
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = 1
            end_idx = -1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[start_idx:end_idx])

        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(text)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        tracker.track_call(
            model=model_name,
            operation="fix_error",
            prompt=fix_prompt,
            response_text="",
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        print(f"LLM 오류 수정 실패: {e}")
        return {"can_fix": False, "analysis": str(e)}


def ask_llm_to_fix_json_error(error_message: str, raw_response: str) -> dict:
    """LLM에게 JSON 파싱 오류 수정을 요청합니다."""
    model_name = 'gemini-2.0-flash'
    model = genai.GenerativeModel(model_name)

    fix_prompt = f"""다음 JSON 파싱 오류를 수정해주세요.

## 오류 메시지
{error_message}

## 원본 응답 (오류가 있는 JSON)
{raw_response[:3000]}  # 너무 길면 자름

## 요청사항
1. JSON 형식 오류를 찾아 수정하세요
2. 특히 이스케이프 문자(\\n, \\t, \\", 등)나 특수문자 문제를 확인하세요
3. LaTeX 수식의 백슬래시가 올바르게 이스케이프되었는지 확인하세요
4. 올바른 JSON 형식으로 수정된 결과를 반환하세요

수정된 JSON만 출력하세요 (설명 없이):
"""

    start_time = time.time()
    try:
        response = model.generate_content(fix_prompt)
        latency_ms = (time.time() - start_time) * 1000
        text = response.text.strip()

        # 사용량 추적
        tracker.track_call(
            model=model_name,
            operation="fix_json",
            prompt=fix_prompt,
            response_text=text,
            latency_ms=latency_ms,
            success=True
        )

        # JSON 파싱
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = 1
            end_idx = -1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[start_idx:end_idx])

        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(text)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        tracker.track_call(
            model=model_name,
            operation="fix_json",
            prompt=fix_prompt,
            response_text="",
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        print(f"JSON 복구 실패: {e}")
        return None


@app.route('/generate-variants', methods=['POST'])
def generate_variants():
    """문제를 기반으로 변형 문제를 생성합니다. SSE로 진행 상황 전송. 자동 복구 기능 포함."""
    from generate_variants import generate_variants_via_code, generate_html_report
    from datetime import datetime

    data = request.get_json()
    question_data = data.get('question')

    if not question_data:
        return jsonify({"success": False, "message": "문제 데이터가 없습니다."}), 400

    # 고유 작업 ID 생성
    task_id = str(uuid.uuid1())
    question_num = question_data.get('question_number', 'unknown')

    def generate():
        nonlocal question_data
        retry_count = 0
        variants_data = None
        last_error = None

        try:
            # 초기 상태
            yield f"data: {json.dumps({'step': 'start', 'progress': 0, 'message': '변형 문제 생성 시작...', 'task_id': task_id})}\n\n"

            # 변형 문제 생성 (진행 상황 yield)
            steps = [
                (5, 'init', '원본 문제 분석 중...'),
                (15, 'generate', 'AI가 변형 문제 생성 중... (10개)'),
            ]

            for progress, step, message in steps:
                yield f"data: {json.dumps({'step': step, 'progress': progress, 'message': message})}\n\n"
                time.sleep(0.1)

            # 자동 복구 루프
            while retry_count <= MAX_AUTO_RETRY:
                try:
                    # 실제 변형 문제 생성
                    if retry_count == 0:
                        yield f"data: {json.dumps({'step': 'generate', 'progress': 20, 'message': 'Gemini API 호출 중...'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'step': 'auto_retry', 'progress': 20, 'message': f'🔄 자동 복구 시도 중... ({retry_count}/{MAX_AUTO_RETRY})', 'retry_count': retry_count})}\n\n"

                    variants_data = generate_variants_via_code(question_data)
                    break  # 성공하면 루프 탈출

                except json.JSONDecodeError as je:
                    last_error = str(je)
                    error_context = "JSON 파싱 오류 - LLM 응답이 올바른 JSON 형식이 아닙니다"
                    print(f"JSON 오류 (시도 {retry_count + 1}): {je}")

                    if retry_count < MAX_AUTO_RETRY:
                        yield f"data: {json.dumps({'step': 'auto_fix', 'progress': 25, 'message': '🤖 AI가 오류를 분석하고 수정 중...', 'error': last_error})}\n\n"

                        # LLM에게 수정 요청
                        fix_result = ask_llm_to_fix_error(last_error, error_context, question_data)

                        if fix_result.get('can_fix') and fix_result.get('fixed_data'):
                            question_data = fix_result['fixed_data']
                            fix_desc = fix_result.get('fix_description', '데이터 수정됨')
                            fix_analysis = fix_result.get('analysis', '')
                            msg = f'✅ 수정 완료: {fix_desc}'
                            yield f"data: {json.dumps({'step': 'auto_fixed', 'progress': 30, 'message': msg, 'analysis': fix_analysis})}\n\n"
                            retry_count += 1
                            continue
                        else:
                            fail_analysis = fix_result.get('analysis', '수정 불가')
                            fail_msg = f'자동 복구 실패: {fail_analysis}'
                            yield f"data: {json.dumps({'step': 'auto_fix_failed', 'progress': 0, 'message': fail_msg})}\n\n"
                            break
                    retry_count += 1

                except ImportError as ie:
                    error_msg = f"Python 모듈 오류: {str(ie)}"
                    yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': error_msg, 'error_type': 'import'})}\n\n"
                    return

                except SyntaxError as se:
                    error_msg = f"Python 문법 오류: {str(se)}"
                    yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': error_msg, 'error_type': 'syntax'})}\n\n"
                    return

                except Exception as e:
                    last_error = str(e)
                    error_str = str(e).lower()

                    # API 관련 오류는 재시도하지 않음
                    if 'api' in error_str or 'quota' in error_str or 'rate' in error_str:
                        error_msg = f"API 오류: {str(e)}"
                        yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': error_msg, 'error_type': 'api'})}\n\n"
                        return

                    print(f"생성 오류 (시도 {retry_count + 1}): {e}")

                    if retry_count < MAX_AUTO_RETRY:
                        yield f"data: {json.dumps({'step': 'auto_fix', 'progress': 25, 'message': '🤖 AI가 오류를 분석하고 수정 중...', 'error': last_error})}\n\n"

                        # LLM에게 수정 요청
                        error_context = f"변형 문제 생성 중 오류 발생"
                        fix_result = ask_llm_to_fix_error(last_error, error_context, question_data)

                        if fix_result.get('can_fix') and fix_result.get('fixed_data'):
                            question_data = fix_result['fixed_data']
                            fix_desc2 = fix_result.get('fix_description', '데이터 수정됨')
                            fix_analysis2 = fix_result.get('analysis', '')
                            msg2 = f'✅ 수정 완료: {fix_desc2}'
                            yield f"data: {json.dumps({'step': 'auto_fixed', 'progress': 30, 'message': msg2, 'analysis': fix_analysis2})}\n\n"
                            retry_count += 1
                            continue
                        else:
                            fail_analysis2 = fix_result.get('analysis', '수정 불가')
                            fail_msg2 = f'자동 복구 실패: {fail_analysis2}'
                            yield f"data: {json.dumps({'step': 'auto_fix_failed', 'progress': 0, 'message': fail_msg2})}\n\n"
                            break
                    retry_count += 1

            # 모든 재시도 실패
            if variants_data is None:
                error_msg = f"변형 문제 생성 실패 (재시도 {retry_count}회): {last_error}"
                yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': error_msg, 'error_type': 'generation', 'retry_exhausted': True})}\n\n"
                return

            yield f"data: {json.dumps({'step': 'generated', 'progress': 50, 'message': '변형 문제 10개 생성 완료' + (f' (재시도 {retry_count}회 후 성공)' if retry_count > 0 else '')})}\n\n"

            # 검증 단계
            variant_count = len(variants_data.get('variants', []))
            yield f"data: {json.dumps({'step': 'verify', 'progress': 55, 'message': f'정답 검증 중... (0/{variant_count + 1})'})}\n\n"

            # 검증은 이미 generate_variants_with_progress에서 수행됨
            yield f"data: {json.dumps({'step': 'verify', 'progress': 80, 'message': f'정답 검증 완료 ({variant_count + 1}개)'})}\n\n"

            # 그래프 생성
            yield f"data: {json.dumps({'step': 'graph', 'progress': 85, 'message': '그래프 생성 중...'})}\n\n"

            # HTML 리포트 생성
            yield f"data: {json.dumps({'step': 'report', 'progress': 90, 'message': 'HTML 리포트 생성 중...'})}\n\n"

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_filename = f'variants_q{question_num}_{timestamp}.html'
            html_path = os.path.join(VARIANTS_FOLDER, html_filename)

            try:
                generate_html_report(question_data, variants_data, html_path)
            except Exception as e:
                error_msg = f"HTML 리포트 생성 실패: {str(e)}"
                yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': error_msg, 'error_type': 'report'})}\n\n"
                return

            # JSON 결과 저장
            json_filename = f'variants_q{question_num}_{timestamp}.json'
            json_path = os.path.join(VARIANTS_FOLDER, json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(variants_data, f, ensure_ascii=False, indent=2)

            yield f"data: {json.dumps({'step': 'save', 'progress': 95, 'message': '파일 저장 완료'})}\n\n"

            # 완료
            result = {
                'step': 'complete',
                'progress': 100,
                'message': '변형 문제 생성 완료!' + (f' (자동 복구 {retry_count}회)' if retry_count > 0 else ''),
                'html_url': f"{SERVER_URL}/variants/{html_filename}",
                'json_url': f"{SERVER_URL}/variants/{json_filename}",
                'variant_count': variant_count,
                'retry_count': retry_count
            }
            yield f"data: {json.dumps(result)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'예기치 않은 오류: {str(e)}', 'error_type': 'unknown'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })


@app.route('/variants/<filename>')
def serve_variant(filename):
    """변형 문제 HTML/JSON 파일을 제공합니다."""
    return send_from_directory(VARIANTS_FOLDER, filename)


@app.route('/variants', methods=['GET'])
def list_variants():
    """생성된 변형 문제 목록을 반환합니다."""
    files = []
    if os.path.exists(VARIANTS_FOLDER):
        for f in os.listdir(VARIANTS_FOLDER):
            if f.endswith('.html'):
                files.append({
                    "filename": f,
                    "url": f"{SERVER_URL}/variants/{f}",
                    "created": os.path.getmtime(os.path.join(VARIANTS_FOLDER, f))
                })
    files.sort(key=lambda x: x['created'], reverse=True)
    return jsonify({"success": True, "files": files})


@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['IMAGES_FOLDER'], filename)


# LLM 사용량 통계 API
@app.route('/llm-stats', methods=['GET'])
def get_llm_stats():
    """LLM API 사용량 통계를 반환합니다."""
    return jsonify({
        "success": True,
        "stats": tracker.get_stats()
    })


@app.route('/llm-stats/reset', methods=['POST'])
def reset_llm_stats():
    """LLM API 사용량 통계를 초기화합니다."""
    tracker.reset_stats()
    return jsonify({
        "success": True,
        "message": "통계가 초기화되었습니다.",
        "stats": tracker.get_stats()
    })


@app.route('/llm-stats/summary', methods=['GET'])
def get_llm_summary():
    """LLM API 사용량 요약을 텍스트로 반환합니다."""
    return jsonify({
        "success": True,
        "summary": tracker.get_summary()
    })


# ==================== 세션 관리 API ====================

def generate_session_id(custom_name=None):
    """세션 ID 생성 (타임스탬프_이름 또는 타임스탬프_uuid)"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if custom_name:
        # 파일명에 안전한 문자만 허용
        safe_name = re.sub(r'[^\w\s가-힣-]', '', custom_name).strip()
        safe_name = re.sub(r'\s+', '_', safe_name)[:50]
        return f"{timestamp}_{safe_name}" if safe_name else f"{timestamp}_{uuid.uuid4().hex[:8]}"
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def get_session_path(session_id):
    """세션 폴더 경로 반환"""
    return os.path.join(app.config['SESSIONS_FOLDER'], session_id)


def load_session_metadata(session_id):
    """세션 메타데이터 로드"""
    session_path = get_session_path(session_id)
    metadata_file = os.path.join(session_path, 'metadata.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_session_metadata(session_id, metadata):
    """세션 메타데이터 저장"""
    session_path = get_session_path(session_id)
    os.makedirs(session_path, exist_ok=True)
    metadata_file = os.path.join(session_path, 'metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


@app.route('/sessions', methods=['GET'])
def list_sessions():
    """모든 세션 목록 반환"""
    sessions = []
    sessions_folder = app.config['SESSIONS_FOLDER']

    if os.path.exists(sessions_folder):
        for session_id in os.listdir(sessions_folder):
            session_path = os.path.join(sessions_folder, session_id)
            if os.path.isdir(session_path):
                metadata = load_session_metadata(session_id)
                if metadata:
                    sessions.append({
                        "id": session_id,
                        "name": metadata.get('name', session_id),
                        "created_at": metadata.get('created_at'),
                        "updated_at": metadata.get('updated_at'),
                        "question_count": metadata.get('question_count', 0),
                        "image_filename": metadata.get('image_filename'),
                        "thumbnail_url": f"{SERVER_URL}/sessions/{session_id}/image"
                    })

    # 최신순 정렬
    sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify({"success": True, "sessions": sessions})

@app.route('/sessions', methods=['POST'])
def create_session():
    """새 세션 생성 및 이미지 분석 - 여러 문제가 있으면 각각 별도 세션으로 분리"""
    if 'image_file' not in request.files:
        return jsonify({"success": False, "message": "이미지 파일이 없습니다."}), 400

    file = request.files['image_file']
    if file.filename == '':
        return jsonify({"success": False, "message": "파일 이름이 비어있습니다."}), 400

    # 원본 파일명에서 확장자 추출 (한글 파일명 대응)
    original_name = file.filename
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"success": False, "message": "지원하지 않는 파일 형식입니다."}), 400

    # 프롬프트
    system_prompt = request.form.get('system_prompt', None)
    user_prompt = request.form.get('user_prompt', None)
    custom_name = request.form.get('session_name', '').strip()

    # 임시 파일로 저장
    temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{uuid.uuid4()}.{ext}")
    file.save(temp_path)

    created_sessions = []  # 예외 처리를 위해 미리 초기화

    try:
        img = Image.open(temp_path)

        # Gemini Vision으로 분석
        result = analyze_exam_image(img, system_prompt, user_prompt)
        questions = result.get('questions', [])

        if len(questions) == 0:
            os.remove(temp_path)
            return jsonify({"success": False, "message": "문제를 찾을 수 없습니다."}), 400

        now = datetime.now().isoformat()

        # 각 문제별로 별도 세션 생성
        for idx, question in enumerate(questions):
            q_num = question.get('question_number', f'Q{idx+1}')

            # 세션 이름 생성: 사용자 지정 이름이 있으면 "이름_문제번호", 없으면 문제번호만
            if custom_name:
                session_name = f"{custom_name}_{q_num}번" if len(questions) > 1 else custom_name
            else:
                session_name = f"{q_num}번 문제"

            session_id = generate_session_id(None)
            session_path = get_session_path(session_id)
            os.makedirs(session_path, exist_ok=True)

            # bounding_box가 있으면 크롭, 없으면 전체 이미지 복사
            image_filename = f"original.{ext}"
            image_path = os.path.join(session_path, image_filename)

            bounding_box = question.get('bounding_box')
            if bounding_box and len(questions) > 1:
                # 여러 문제가 있을 때만 크롭 적용
                cropped_img = crop_image_by_bbox(img, bounding_box)
                cropped_img.save(image_path)
                # 크롭된 이미지 URL을 question 데이터에 추가 (여러 문제일 때만)
                question['cropped_image_url'] = f"{SERVER_URL}/sessions/{session_id}/image"
            else:
                # 단일 문제거나 bounding_box가 없으면 전체 이미지 복사
                shutil.copy2(temp_path, image_path)

            # 그래프 생성 (graph_info가 있으면)
            graph_info = question.get('graph_info')
            if graph_info and graph_info.get('type') and graph_info.get('plot_data'):
                try:
                    graph_filename = f"graph_q{q_num}.png"
                    graph_path = os.path.join(session_path, graph_filename)
                    generate_graph(graph_info, graph_path)
                    question['graph_url'] = f"{SERVER_URL}/sessions/{session_id}/files/{graph_filename}"
                except Exception as graph_error:
                    print(f"Graph generation error: {graph_error}")
                    question['graph_error'] = str(graph_error)

            # 단일 문제 결과 저장
            single_result = {"questions": [question]}
            analysis_file = os.path.join(session_path, 'analysis.json')
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(single_result, f, ensure_ascii=False, indent=2)

            # 메타데이터 저장
            metadata = {
                "name": session_name,
                "created_at": now,
                "updated_at": now,
                "image_filename": image_filename,
                "original_filename": original_name,
                "question_count": 1,
                "system_prompt_used": system_prompt,
                "user_prompt_used": user_prompt
            }
            save_session_metadata(session_id, metadata)

            created_sessions.append({
                "session_id": session_id,
                "name": session_name,
                "question_number": q_num,
                "image_url": f"{SERVER_URL}/sessions/{session_id}/image",
                "data": single_result
            })

        # 임시 파일 삭제
        os.remove(temp_path)

        # 첫 번째 세션을 메인으로 반환 (하위 호환성)
        first_session = created_sessions[0]
        return jsonify({
            "success": True,
            "session_id": first_session['session_id'],
            "name": first_session['name'],
            "question_count": 1,
            "image_url": first_session['image_url'],
            "data": first_session['data'],
            "created_sessions": created_sessions,  # 모든 생성된 세션 정보
            "total_questions": len(questions)
        })

    except Exception as e:
        # 실패 시 임시 파일 및 생성된 세션 폴더들 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
        for session_info in created_sessions:
            session_folder = get_session_path(session_info['session_id'])
            if os.path.exists(session_folder):
                shutil.rmtree(session_folder)
        print(f"Session creation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"분석 중 오류 발생: {str(e)}"}), 500


@app.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """세션 상세 정보 조회"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    metadata = load_session_metadata(session_id)
    if not metadata:
        return jsonify({"success": False, "message": "메타데이터를 찾을 수 없습니다."}), 404

    # 분석 결과 로드
    analysis_file = os.path.join(session_path, 'analysis.json')
    analysis_data = None
    if os.path.exists(analysis_file):
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "name": metadata.get('name', session_id),
        "created_at": metadata.get('created_at'),
        "updated_at": metadata.get('updated_at'),
        "question_count": metadata.get('question_count', 0),
        "image_url": f"{SERVER_URL}/sessions/{session_id}/image",
        "data": analysis_data
    })


@app.route('/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """세션 이름 수정"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    data = request.get_json()
    new_name = data.get('name', '').strip()

    if not new_name:
        return jsonify({"success": False, "message": "새 이름이 필요합니다."}), 400

    metadata = load_session_metadata(session_id)
    if metadata:
        metadata['name'] = new_name
        metadata['updated_at'] = datetime.now().isoformat()
        save_session_metadata(session_id, metadata)

    return jsonify({
        "success": True,
        "message": "세션 이름이 수정되었습니다.",
        "session_id": session_id,
        "name": new_name
    })


@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """세션 삭제"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    try:
        shutil.rmtree(session_path)
        return jsonify({
            "success": True,
            "message": "세션이 삭제되었습니다.",
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"삭제 중 오류 발생: {str(e)}"}), 500


@app.route('/sessions/<session_id>/reanalyze', methods=['POST'])
def reanalyze_session(session_id):
    """세션 재분석"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    metadata = load_session_metadata(session_id)
    if not metadata:
        return jsonify({"success": False, "message": "메타데이터를 찾을 수 없습니다."}), 404

    # 프롬프트 (요청에서 받거나 기존 것 사용)
    data = request.get_json() or {}
    system_prompt = data.get('system_prompt', metadata.get('system_prompt_used'))
    user_prompt = data.get('user_prompt', metadata.get('user_prompt_used'))

    # 이미지 로드
    image_filename = metadata.get('image_filename', 'original.png')
    image_path = os.path.join(session_path, image_filename)

    if not os.path.exists(image_path):
        return jsonify({"success": False, "message": "이미지 파일을 찾을 수 없습니다."}), 404

    try:
        img = Image.open(image_path)

        # Gemini Vision으로 재분석
        result = analyze_exam_image(img, system_prompt, user_prompt)
        question_count = len(result.get('questions', []))

        # 기존 그래프 파일 삭제
        for f in os.listdir(session_path):
            if f.startswith('graph_'):
                os.remove(os.path.join(session_path, f))

        # 각 문항의 graph_info가 있으면 그래프 생성
        for question in result.get('questions', []):
            graph_info = question.get('graph_info')
            if graph_info and graph_info.get('type') and graph_info.get('plot_data'):
                try:
                    q_num = question.get('question_number', 'unknown')
                    graph_filename = f"graph_q{q_num}.png"
                    graph_path = os.path.join(session_path, graph_filename)
                    generate_graph(graph_info, graph_path)
                    question['graph_url'] = f"{SERVER_URL}/sessions/{session_id}/files/{graph_filename}"
                except Exception as graph_error:
                    print(f"Graph generation error: {graph_error}")
                    question['graph_error'] = str(graph_error)

        # 분석 결과 저장
        analysis_file = os.path.join(session_path, 'analysis.json')
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 메타데이터 업데이트
        metadata['updated_at'] = datetime.now().isoformat()
        metadata['question_count'] = question_count
        metadata['system_prompt_used'] = system_prompt
        metadata['user_prompt_used'] = user_prompt
        save_session_metadata(session_id, metadata)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "재분석 완료",
            "question_count": question_count,
            "data": result
        })

    except Exception as e:
        print(f"Reanalysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"재분석 중 오류 발생: {str(e)}"}), 500


@app.route('/sessions/<session_id>/image')
def serve_session_image(session_id):
    """세션의 원본 이미지 제공"""
    session_path = get_session_path(session_id)
    metadata = load_session_metadata(session_id)

    if not metadata:
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    image_filename = metadata.get('image_filename', 'original.png')
    return send_from_directory(session_path, image_filename)


@app.route('/sessions/<session_id>/files/<filename>')
def serve_session_file(session_id, filename):
    """세션의 파일 제공 (그래프 등)"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    return send_from_directory(session_path, filename)


# ==================== 세션별 변형 문제 API ====================

@app.route('/sessions/<session_id>/variants', methods=['GET'])
def get_session_variants(session_id):
    """세션의 모든 변형 문제 목록 조회"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    variants_folder = os.path.join(session_path, 'variants')
    variants = []

    if os.path.exists(variants_folder):
        for f in os.listdir(variants_folder):
            if f.endswith('.json') and f.startswith('q'):
                # q{question_num}_{timestamp}.json 형식
                parts = f.replace('.json', '').split('_')
                question_num = parts[0][1:]  # 'q' 제거
                timestamp = '_'.join(parts[1:]) if len(parts) > 1 else ''

                json_path = os.path.join(variants_folder, f)
                html_filename = f.replace('.json', '.html')

                variants.append({
                    "question_number": question_num,
                    "json_filename": f,
                    "html_filename": html_filename,
                    "timestamp": timestamp,
                    "created": os.path.getmtime(json_path),
                    "json_url": f"{SERVER_URL}/sessions/{session_id}/variants/{f}",
                    "html_url": f"{SERVER_URL}/sessions/{session_id}/variants/{html_filename}"
                })

    # 문제 번호별로 정렬 후 최신순
    variants.sort(key=lambda x: (x['question_number'], -x['created']))

    return jsonify({"success": True, "variants": variants})


@app.route('/sessions/<session_id>/variants/<filename>')
def serve_session_variant(session_id, filename):
    """세션의 변형 문제 파일 제공"""
    session_path = get_session_path(session_id)
    variants_folder = os.path.join(session_path, 'variants')

    if not os.path.exists(variants_folder):
        return jsonify({"success": False, "message": "변형 문제 폴더를 찾을 수 없습니다."}), 404

    return send_from_directory(variants_folder, filename)


@app.route('/sessions/<session_id>/variants/question/<question_num>', methods=['GET'])
def get_question_variants(session_id, question_num):
    """특정 문항의 변형 문제 목록 조회"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    variants_folder = os.path.join(session_path, 'variants')
    variants = []

    if os.path.exists(variants_folder):
        for f in os.listdir(variants_folder):
            if f.startswith(f'q{question_num}_') and f.endswith('.json'):
                timestamp = f.replace(f'q{question_num}_', '').replace('.json', '')
                json_path = os.path.join(variants_folder, f)
                html_filename = f.replace('.json', '.html')

                # JSON 데이터 로드하여 변형 문제 개수 등 추가 정보 확인
                variant_count = 0
                try:
                    with open(json_path, 'r', encoding='utf-8') as jf:
                        data = json.load(jf)
                        variant_count = len(data.get('variants', []))
                except:
                    pass

                variants.append({
                    "json_filename": f,
                    "html_filename": html_filename,
                    "timestamp": timestamp,
                    "created": os.path.getmtime(json_path),
                    "variant_count": variant_count,
                    "json_url": f"{SERVER_URL}/sessions/{session_id}/variants/{f}",
                    "html_url": f"{SERVER_URL}/sessions/{session_id}/variants/{html_filename}"
                })

    # 최신순 정렬
    variants.sort(key=lambda x: -x['created'])

    return jsonify({
        "success": True,
        "question_number": question_num,
        "variants": variants,
        "has_variants": len(variants) > 0
    })


@app.route('/sessions/<session_id>/generate-variants', methods=['POST'])
def generate_session_variants(session_id):
    """세션 내 문항의 변형 문제 생성 (SSE, 세션 폴더에 저장)

    메타코드 생성 방식으로 변형 문제를 생성합니다.
    """
    from generate_variants import generate_variants_via_code, generate_html_report

    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    data = request.get_json()
    question_data = data.get('question')

    if not question_data:
        return jsonify({"success": False, "message": "문제 데이터가 없습니다."}), 400

    # 고유 작업 ID 생성
    task_id = str(uuid.uuid1())
    question_num = question_data.get('question_number', 'unknown')

    # 세션의 variants 폴더 생성
    variants_folder = os.path.join(session_path, 'variants')
    os.makedirs(variants_folder, exist_ok=True)

    def generate():
        nonlocal question_data
        import queue
        import threading

        retry_count = 0
        variants_data = None
        last_error = None

        # 진행 상황을 저장할 큐
        progress_queue = queue.Queue()

        def progress_callback(step, progress, message, details):
            """콜백으로 받은 진행 상황을 큐에 추가"""
            progress_queue.put({
                'step': step,
                'progress': progress,
                'message': message,
                **details
            })

        try:
            # 초기 상태
            yield f"data: {json.dumps({'step': 'start', 'progress': 0, 'message': '변형 문제 생성 시작...', 'task_id': task_id})}\n\n"

            # 자동 복구 루프
            while retry_count <= MAX_AUTO_RETRY:
                try:
                    # 실제 변형 문제 생성
                    if retry_count == 0:
                        yield f"data: {json.dumps({'step': 'generate', 'progress': 5, 'message': 'Gemini API로 메타코드 생성 중...'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'step': 'auto_retry', 'progress': 5, 'message': f'자동 복구 시도 중... ({retry_count}/{MAX_AUTO_RETRY})', 'retry_count': retry_count})}\n\n"

                    # 백그라운드 스레드에서 생성 실행
                    result_holder = {'data': None, 'error': None}

                    def run_generation():
                        try:
                            result_holder['data'] = generate_variants_via_code(
                                question_data,
                                progress_callback=progress_callback
                            )
                        except Exception as e:
                            result_holder['error'] = e

                    thread = threading.Thread(target=run_generation)
                    thread.start()

                    # 스레드가 완료될 때까지 큐에서 진행 상황 읽어서 전송
                    while thread.is_alive():
                        try:
                            progress_data = progress_queue.get(timeout=0.5)
                            yield f"data: {json.dumps(progress_data)}\n\n"
                        except queue.Empty:
                            continue

                    # 남은 큐 비우기
                    while not progress_queue.empty():
                        progress_data = progress_queue.get_nowait()
                        yield f"data: {json.dumps(progress_data)}\n\n"

                    thread.join()

                    if result_holder['error']:
                        raise result_holder['error']

                    variants_data = result_holder['data']
                    break  # 성공하면 루프 탈출

                except json.JSONDecodeError as je:
                    last_error = str(je)
                    error_context = "JSON 파싱 오류 - LLM 응답이 올바른 JSON 형식이 아닙니다"
                    print(f"JSON 오류 (시도 {retry_count + 1}): {je}")

                    if retry_count < MAX_AUTO_RETRY:
                        yield f"data: {json.dumps({'step': 'auto_fix', 'progress': 25, 'message': 'AI가 오류를 분석하고 수정 중...', 'error': last_error})}\n\n"

                        # LLM에게 수정 요청
                        fix_result = ask_llm_to_fix_error(last_error, error_context, question_data)

                        if fix_result.get('can_fix') and fix_result.get('fixed_data'):
                            question_data = fix_result['fixed_data']
                            retry_count += 1
                            continue
                    retry_count += 1

                except Exception as e:
                    last_error = str(e)
                    error_str = str(e).lower()

                    if 'api' in error_str or 'quota' in error_str or 'rate' in error_str:
                        yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'API 오류: {str(e)}', 'error_type': 'api'})}\n\n"
                        return

                    print(f"생성 오류 (시도 {retry_count + 1}): {e}")

                    if retry_count < MAX_AUTO_RETRY:
                        yield f"data: {json.dumps({'step': 'auto_fix', 'progress': 25, 'message': 'AI가 오류를 분석하고 수정 중...', 'error': last_error})}\n\n"
                        fix_result = ask_llm_to_fix_error(last_error, "변형 문제 생성 중 오류 발생", question_data)

                        if fix_result.get('can_fix') and fix_result.get('fixed_data'):
                            question_data = fix_result['fixed_data']
                            retry_count += 1
                            continue
                    retry_count += 1

            # 모든 재시도 실패
            if variants_data is None:
                yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'변형 문제 생성 실패: {last_error}', 'error_type': 'generation'})}\n\n"
                return

            # 생성된 코드 정보 추가
            generated_code = variants_data.get('generated_code', '')
            yield f"data: {json.dumps({'step': 'generated', 'progress': 50, 'message': '변형 문제 10개 생성 완료', 'code_length': len(generated_code)})}\n\n"

            # 검증 단계
            variant_count = len(variants_data.get('variants', []))
            yield f"data: {json.dumps({'step': 'verify', 'progress': 80, 'message': f'정답 검증 완료 ({variant_count + 1}개)'})}\n\n"

            # HTML 리포트 생성
            yield f"data: {json.dumps({'step': 'report', 'progress': 90, 'message': 'HTML 리포트 생성 중...'})}\n\n"

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_filename = f'q{question_num}_{timestamp}.html'
            json_filename = f'q{question_num}_{timestamp}.json'
            html_path = os.path.join(variants_folder, html_filename)
            json_path = os.path.join(variants_folder, json_filename)

            # 변형 문제 최대 10개 제한 - 오래된 파일 삭제
            MAX_VARIANTS_PER_QUESTION = 10
            existing_html_files = sorted([
                f for f in os.listdir(variants_folder)
                if f.startswith(f'q{question_num}_') and f.endswith('.html')
            ])
            # 새 파일 추가 후 10개를 초과하면 가장 오래된 것부터 삭제
            while len(existing_html_files) >= MAX_VARIANTS_PER_QUESTION:
                oldest_html = existing_html_files.pop(0)
                oldest_json = oldest_html.replace('.html', '.json')
                try:
                    os.remove(os.path.join(variants_folder, oldest_html))
                    json_to_delete = os.path.join(variants_folder, oldest_json)
                    if os.path.exists(json_to_delete):
                        os.remove(json_to_delete)
                    print(f"  🗑️ 오래된 변형 문제 삭제: {oldest_html}")
                except Exception as del_e:
                    print(f"  ⚠️ 파일 삭제 실패: {del_e}")

            try:
                generate_html_report(question_data, variants_data, html_path)
            except Exception as e:
                yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'HTML 리포트 생성 실패: {str(e)}', 'error_type': 'report'})}\n\n"
                return

            # JSON 결과 저장
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(variants_data, f, ensure_ascii=False, indent=2)

            # Python 코드 파일 저장
            py_filename = None
            if variants_data.get('generated_code'):
                py_filename = f'q{question_num}_{timestamp}_code.py'
                py_path = os.path.join(variants_folder, py_filename)
                with open(py_path, 'w', encoding='utf-8') as f:
                    # 헤더 주석 추가
                    f.write(f'''# 자동 생성된 변형 문제 생성 코드
# 원본 문제: {question_num}번
# 생성 시각: {timestamp}
#
# 사용 방법:
#   from {py_filename[:-3]} import generate_variant
#   variant = generate_variant("쉬움", 1)  # 난이도: 쉬움/보통/어려움

import random
import math

''')
                    f.write(variants_data['generated_code'])
                print(f"  📄 Python 코드 저장: {py_filename}")

            yield f"data: {json.dumps({'step': 'save', 'progress': 95, 'message': '파일 저장 완료'})}\n\n"

            # 완료
            result = {
                'step': 'complete',
                'progress': 100,
                'message': '변형 문제 생성 완료!',
                'html_url': f"{SERVER_URL}/sessions/{session_id}/variants/{html_filename}",
                'json_url': f"{SERVER_URL}/sessions/{session_id}/variants/{json_filename}",
                'variant_count': variant_count,
                'retry_count': retry_count,
                'saved_to_session': True
            }
            # Python 코드 URL 추가
            if py_filename:
                result['py_url'] = f"{SERVER_URL}/sessions/{session_id}/variants/{py_filename}"
            yield f"data: {json.dumps(result)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'예기치 않은 오류: {str(e)}', 'error_type': 'unknown'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })


@app.route('/sessions/<session_id>/variants/question/<question_num>', methods=['DELETE'])
def delete_question_variants(session_id, question_num):
    """특정 문항의 변형 문제 삭제"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    variants_folder = os.path.join(session_path, 'variants')
    deleted_count = 0

    if os.path.exists(variants_folder):
        for f in os.listdir(variants_folder):
            if f.startswith(f'q{question_num}_'):
                os.remove(os.path.join(variants_folder, f))
                deleted_count += 1

    return jsonify({
        "success": True,
        "message": f"{question_num}번 문항의 변형 문제 {deleted_count}개가 삭제되었습니다.",
        "deleted_count": deleted_count
    })


@app.route('/sessions/<session_id>/generate-exam', methods=['POST'])
def generate_exam(session_id):
    """세션의 변형 문제들로 수능 스타일 문제지 생성"""
    from generate_exam import generate_exam_html
    import random

    session_path = get_session_path(session_id)
    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    # variants 폴더에서 변형 문제 JSON 수집
    variants_folder = os.path.join(session_path, 'variants')
    if not os.path.exists(variants_folder):
        return jsonify({"success": False, "message": "변형 문제가 없습니다. 먼저 변형 문제를 생성해주세요."}), 404

    # 모든 변형 문제 수집
    all_variants = []
    variant_json_files = [f for f in os.listdir(variants_folder) if f.endswith('.json') and not f.endswith('_code.json')]

    for json_file in variant_json_files:
        json_path = os.path.join(variants_folder, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                variant_data = json.load(f)

            # variants 배열에서 문제 추출
            for variant in variant_data.get('variants', []):
                # 문제지용 형식으로 변환
                q = {
                    'question_number': str(variant.get('variant_id', '')),
                    'question_text': variant.get('question_text', ''),
                    'choices': variant.get('choices', []),
                    'answer': variant.get('answer', ''),
                    'explanation': variant.get('explanation', ''),
                    'difficulty': variant.get('difficulty', '중'),
                    'points': 3,  # 기본 배점
                    'has_passage': False,
                    'passage': None,
                    'has_figure': False,
                    'figure_description': None
                }
                all_variants.append(q)
        except Exception as e:
            print(f"변형 문제 로드 오류 ({json_file}): {e}")
            continue

    if not all_variants:
        return jsonify({"success": False, "message": "유효한 변형 문제가 없습니다."}), 400

    # 요청 파라미터
    data = request.get_json() or {}
    question_count = min(data.get('question_count', 5), len(all_variants))
    difficulty = data.get('difficulty', 'mixed')
    title = data.get('title', '수학 모의고사')
    include_answer_sheet = data.get('include_answer_sheet', True)

    # 문항 선택 (난이도 필터링)
    selected_questions = []
    difficulty_map = {'easy': '쉬움', 'medium': '보통', 'hard': '어려움'}

    if difficulty == 'mixed':
        # 랜덤하게 섞어서 선택
        random.shuffle(all_variants)
        selected_questions = all_variants[:question_count]
    else:
        target_level = difficulty_map.get(difficulty, '보통')
        # 해당 난이도 문제 필터링
        filtered = [q for q in all_variants if q.get('difficulty') == target_level]
        random.shuffle(filtered)
        selected_questions = filtered[:question_count]

        # 부족한 경우 다른 문제로 채우기
        if len(selected_questions) < question_count:
            remaining = [q for q in all_variants if q not in selected_questions]
            random.shuffle(remaining)
            selected_questions.extend(remaining[:question_count - len(selected_questions)])

    # 문항 번호 재부여
    for idx, q in enumerate(selected_questions, 1):
        q['question_number'] = str(idx)

    # exams 폴더 생성
    exams_folder = os.path.join(session_path, 'exams')
    os.makedirs(exams_folder, exist_ok=True)

    # 파일명 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'exam_{timestamp}.html'
    filepath = os.path.join(exams_folder, filename)

    # HTML 생성
    html_content = generate_exam_html(
        questions=selected_questions,
        title=title,
        include_answer_sheet=include_answer_sheet
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return jsonify({
        "success": True,
        "exam_url": f"{SERVER_URL}/sessions/{session_id}/exams/{filename}",
        "question_count": len(selected_questions)
    })


@app.route('/sessions/<session_id>/exams/<filename>')
def get_exam_file(session_id, filename):
    """문제지 파일 제공"""
    session_path = get_session_path(session_id)
    exams_folder = os.path.join(session_path, 'exams')
    filepath = os.path.join(exams_folder, filename)

    if os.path.exists(filepath):
        return send_file(filepath, mimetype='text/html')
    return jsonify({"success": False, "message": "파일을 찾을 수 없습니다."}), 404


# ==================== 문항 분석 API ====================

@app.route('/sessions/<session_id>/analyze-question', methods=['POST'])
def analyze_session_question(session_id):
    """문항 심층 분석 (SSE로 진행 상황 전송)"""
    from analyze_question import analyze_question, generate_analysis_html

    session_path = get_session_path(session_id)
    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    data = request.get_json()
    question_data = data.get('question')

    if not question_data:
        return jsonify({"success": False, "message": "문제 데이터가 없습니다."}), 400

    task_id = str(uuid.uuid1())
    question_num = question_data.get('question_number', 'unknown')

    # 분석 결과 폴더 생성
    analysis_folder = os.path.join(session_path, 'analysis')
    os.makedirs(analysis_folder, exist_ok=True)

    def generate():
        import queue
        import threading

        progress_queue = queue.Queue()

        def progress_callback(step, progress, message, details):
            progress_queue.put({
                'step': step,
                'progress': progress,
                'message': message,
                **details
            })

        try:
            yield f"data: {json.dumps({'step': 'start', 'progress': 0, 'message': '문항 분석 시작...', 'task_id': task_id})}\n\n"

            result_holder = {'data': None, 'error': None}

            def run_analysis():
                try:
                    result_holder['data'] = analyze_question(
                        question_data,
                        progress_callback=progress_callback
                    )
                except Exception as e:
                    result_holder['error'] = e

            thread = threading.Thread(target=run_analysis)
            thread.start()

            while thread.is_alive():
                try:
                    progress_data = progress_queue.get(timeout=0.5)
                    yield f"data: {json.dumps(progress_data)}\n\n"
                except queue.Empty:
                    continue

            while not progress_queue.empty():
                progress_data = progress_queue.get_nowait()
                yield f"data: {json.dumps(progress_data)}\n\n"

            thread.join()

            if result_holder['error']:
                raise result_holder['error']

            analysis_result = result_holder['data']

            if not analysis_result.get('success'):
                yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': analysis_result.get('error', '분석 실패')})}\n\n"
                return

            yield f"data: {json.dumps({'step': 'save', 'progress': 90, 'message': 'HTML 리포트 생성 중...'})}\n\n"

            # HTML 생성 및 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_filename = f'q{question_num}_{timestamp}.html'
            json_filename = f'q{question_num}_{timestamp}.json'
            html_path = os.path.join(analysis_folder, html_filename)
            json_path = os.path.join(analysis_folder, json_filename)

            html_content = generate_analysis_html(question_data, analysis_result)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)

            yield f"data: {json.dumps({'step': 'save', 'progress': 95, 'message': '파일 저장 완료'})}\n\n"

            result = {
                'step': 'complete',
                'progress': 100,
                'message': '문항 분석 완료!',
                'html_url': f"{SERVER_URL}/sessions/{session_id}/analysis/{html_filename}",
                'json_url': f"{SERVER_URL}/sessions/{session_id}/analysis/{json_filename}",
                'analysis': analysis_result.get('analysis', {})
            }
            yield f"data: {json.dumps(result)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'예기치 않은 오류: {str(e)}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })


@app.route('/sessions/<session_id>/analysis/<filename>')
def serve_analysis_file(session_id, filename):
    """분석 결과 파일 제공"""
    session_path = get_session_path(session_id)
    analysis_folder = os.path.join(session_path, 'analysis')

    if not os.path.exists(analysis_folder):
        return jsonify({"success": False, "message": "분석 폴더를 찾을 수 없습니다."}), 404

    return send_from_directory(analysis_folder, filename)


@app.route('/sessions/<session_id>/analysis', methods=['GET'])
def get_session_analysis_list(session_id):
    """세션의 분석 결과 목록 조회"""
    session_path = get_session_path(session_id)

    if not os.path.exists(session_path):
        return jsonify({"success": False, "message": "세션을 찾을 수 없습니다."}), 404

    analysis_folder = os.path.join(session_path, 'analysis')
    analyses = []

    if os.path.exists(analysis_folder):
        for f in os.listdir(analysis_folder):
            if f.endswith('.json') and f.startswith('q'):
                parts = f.replace('.json', '').split('_')
                question_num = parts[0][1:]
                timestamp = '_'.join(parts[1:]) if len(parts) > 1 else ''

                json_path = os.path.join(analysis_folder, f)
                html_filename = f.replace('.json', '.html')

                analyses.append({
                    "question_number": question_num,
                    "json_filename": f,
                    "html_filename": html_filename,
                    "timestamp": timestamp,
                    "created": os.path.getmtime(json_path),
                    "json_url": f"{SERVER_URL}/sessions/{session_id}/analysis/{f}",
                    "html_url": f"{SERVER_URL}/sessions/{session_id}/analysis/{html_filename}"
                })

    analyses.sort(key=lambda x: (x['question_number'], -x['created']))

    return jsonify({"success": True, "analyses": analyses})


if __name__ == '__main__':
    print(f"Flask Server running on http://127.0.0.1:{PORT}")
    app.run(port=PORT, debug=True)
