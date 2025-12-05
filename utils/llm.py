# utils/llm.py
"""LLM 관련 유틸리티 (오류 복구 등)"""

import json
import re
import time
import google.generativeai as genai
from llm_tracker import tracker


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
