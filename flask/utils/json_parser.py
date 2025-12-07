# utils/json_parser.py
"""JSON 파싱 및 수정 유틸리티"""

import json
import re


def restore_latex_escapes(obj):
    """
    JSON 파싱 후 손상된 LaTeX 이스케이프 시퀀스를 복원합니다.
    \f -> \frac, \t -> \times 등의 변환을 수정합니다.
    """
    # 이스케이프 문자 -> LaTeX 명령어 매핑
    escape_map = {
        '\f': '\\f',      # form feed -> \f (for \frac, \forall, etc.)
        '\t': '\\t',      # tab -> \t (for \times, \theta, etc.)
        '\n': '\\n',      # newline -> \n (for \nu, \nabla, etc.)
        '\r': '\\r',      # carriage return -> \r (for \rho, \right, etc.)
        '\b': '\\b',      # backspace -> \b (for \beta, \bar, etc.)
    }

    if isinstance(obj, str):
        result = obj
        for escape_char, latex_prefix in escape_map.items():
            result = result.replace(escape_char, latex_prefix)
        return result
    elif isinstance(obj, dict):
        return {k: restore_latex_escapes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [restore_latex_escapes(item) for item in obj]
    else:
        return obj


def fix_json_escape(text: str) -> str:
    """
    JSON 문자열에서 LaTeX 백슬래시 등 잘못된 이스케이프 시퀀스를 수정합니다.
    """
    result = []
    in_string = False
    i = 0

    while i < len(text):
        char = text[i]

        # 문자열 시작/종료 감지
        if char == '"':
            # 이스케이프된 따옴표인지 확인 (홀수 개의 백슬래시 뒤에 있는 경우)
            num_backslashes = 0
            j = i - 1
            while j >= 0 and text[j] == '\\':
                num_backslashes += 1
                j -= 1
            # 짝수 개의 백슬래시(0 포함) 뒤의 따옴표는 문자열 경계
            if num_backslashes % 2 == 0:
                in_string = not in_string
            result.append(char)
            i += 1
            continue

        # 문자열 내부에서 백슬래시 처리
        if in_string and char == '\\' and i + 1 < len(text):
            next_char = text[i + 1]
            # 유효한 JSON 이스케이프 시퀀스: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
            valid_escapes = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}

            # 이미 이중 백슬래시인 경우 (\\) - 그대로 유지하고 둘 다 건너뜀
            if next_char == '\\':
                result.append('\\\\')
                i += 2
                continue

            if next_char not in valid_escapes:
                # LaTeX 명령어 등의 무효한 이스케이프 -> 백슬래시를 이중으로
                result.append('\\\\')
                i += 1
                continue

        result.append(char)
        i += 1

    return ''.join(result)


def fix_latex_in_json(text: str) -> str:
    """
    JSON 문자열 내의 LaTeX 백슬래시를 이중 백슬래시로 변환합니다.
    더 안전한 문자 단위 처리 방식을 사용합니다.
    """
    result = []
    i = 0
    n = len(text)

    # 유효한 JSON 이스케이프 문자 (표준: ", \, /, b, f, n, r, t, u)
    # 참고: \{ \}는 JSON 표준이 아니므로 \\{ \\}로 변환해야 함
    valid_json_escapes = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}

    while i < n:
        char = text[i]

        if char == '\\' and i + 1 < n:
            next_char = text[i + 1]

            # 이미 이중 백슬래시인 경우 그대로 유지
            if next_char == '\\':
                result.append('\\\\')
                i += 2
                continue

            # 유효한 JSON 이스케이프인 경우 그대로 유지
            if next_char in valid_json_escapes:
                result.append(char)
                i += 1
                continue

            # \uXXXX 유니코드 이스케이프 처리
            if next_char == 'u' and i + 5 < n:
                hex_chars = text[i+2:i+6]
                if all(c in '0123456789abcdefABCDEF' for c in hex_chars):
                    result.append(char)
                    i += 1
                    continue

            # 유효하지 않은 이스케이프 -> 백슬래시를 이중으로
            result.append('\\\\')
            i += 1
            continue

        result.append(char)
        i += 1

    return ''.join(result)


def parse_gemini_json(response_text):
    """Gemini 응답에서 JSON을 파싱합니다. LaTeX 이스케이프 문제도 처리합니다."""
    text = response_text.strip()

    # 마크다운 코드블록 제거
    if text.startswith('```'):
        lines = text.split('\n')
        start_idx = 1
        end_idx = -1 if lines[-1].strip() == '```' else len(lines)
        text = '\n'.join(lines[start_idx:end_idx])

    # JSON 객체 또는 배열 찾기
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if json_match:
        json_text = json_match.group()
    else:
        json_text = text

    # 1차 시도: 직접 파싱
    try:
        result = json.loads(json_text)
        return restore_latex_escapes(result)
    except json.JSONDecodeError:
        pass

    # 2차 시도: 이스케이프 수정 후 파싱
    try:
        fixed = fix_json_escape(json_text)
        result = json.loads(fixed)
        return restore_latex_escapes(result)
    except json.JSONDecodeError:
        pass

    # 3차 시도: LaTeX 전용 수정
    try:
        fixed = fix_latex_in_json(json_text)
        result = json.loads(fixed)
        return restore_latex_escapes(result)
    except json.JSONDecodeError:
        pass

    # 4차 시도: 제어 문자 제거 후 파싱
    try:
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_text)
        fixed = fix_json_escape(cleaned)
        result = json.loads(fixed)
        return restore_latex_escapes(result)
    except json.JSONDecodeError:
        pass

    # 5차 시도: 모든 수정 적용
    try:
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_text)
        fixed = fix_latex_in_json(cleaned)
        fixed = fix_json_escape(fixed)
        result = json.loads(fixed)
        return restore_latex_escapes(result)
    except json.JSONDecodeError as e:
        # 디버깅을 위해 문제 위치 출력
        print(f"JSON 파싱 실패: {e}")
        print(f"문제 위치 주변: ...{json_text[max(0,e.pos-50):e.pos+50]}...")
        raise e
