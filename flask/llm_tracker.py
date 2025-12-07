# llm_tracker.py
"""
LLM API 사용량 추적 모듈
- 모델별 사용량 추적
- 토큰 카운팅 (입력/출력)
- 비용 추정
- 파일 저장/로드로 누적 통계 유지
"""

import time
import os
from datetime import datetime
from threading import Lock
from dataclasses import dataclass, field, asdict
from typing import Optional
import json

# 통계 저장 파일 경로 (GEN_DATA_PATH 환경변수 사용)
from dotenv import load_dotenv
load_dotenv()

GEN_DATA_PATH = os.path.expanduser(os.environ.get('GEN_DATA_PATH', '~/.gen-data'))
STATS_FILE = os.path.join(GEN_DATA_PATH, 'data', 'llm_stats.json')


# Gemini 모델별 가격 (1000 토큰당 USD, 2025년 기준)
GEMINI_PRICING = {
    "gemini-2.5-pro": {
        "input": 0.00125,      # $1.25 per 1M tokens
        "output": 0.01         # $10.00 per 1M tokens
    },
    "gemini-2.5-flash": {
        "input": 0.000015,     # $0.015 per 1M tokens
        "output": 0.00006      # $0.06 per 1M tokens
    },
    "gemini-2.0-flash": {
        "input": 0.00001875,   # $0.01875 per 1M tokens = $0.00001875 per 1K
        "output": 0.000075     # $0.075 per 1M tokens = $0.000075 per 1K
    },
    "gemini-2.0-flash-exp": {
        "input": 0.00001875,
        "output": 0.000075
    },
    "gemini-1.5-flash": {
        "input": 0.00001875,
        "output": 0.000075
    },
    "gemini-1.5-pro": {
        "input": 0.00125,      # $1.25 per 1M tokens
        "output": 0.005        # $5.00 per 1M tokens
    }
}

# 기본 가격 (알 수 없는 모델용)
DEFAULT_PRICING = {
    "input": 0.0001,
    "output": 0.0003
}


@dataclass
class APICall:
    """단일 API 호출 정보"""
    timestamp: str
    model: str
    operation: str  # 'analyze', 'generate_variants', 'verify', 'fix_error' 등
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    latency_ms: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class UsageStats:
    """세션 사용량 통계"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    calls_by_model: dict = field(default_factory=dict)
    calls_by_operation: dict = field(default_factory=dict)
    call_history: list = field(default_factory=list)
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())


class LLMTracker:
    """LLM API 사용량 추적기"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._call_lock = Lock()
        self.stats = self._load_stats()

    def _load_stats(self) -> UsageStats:
        """파일에서 통계를 로드합니다"""
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stats = UsageStats(
                        total_calls=data.get('total_calls', 0),
                        successful_calls=data.get('successful_calls', 0),
                        failed_calls=data.get('failed_calls', 0),
                        total_input_tokens=data.get('total_input_tokens', 0),
                        total_output_tokens=data.get('total_output_tokens', 0),
                        total_cost=data.get('total_cost', 0.0),
                        calls_by_model=data.get('calls_by_model', {}),
                        calls_by_operation=data.get('calls_by_operation', {}),
                        call_history=data.get('call_history', [])[-100:],  # 최근 100개만
                        session_start=data.get('first_call', datetime.now().isoformat())
                    )
                    print(f"📊 LLM 통계 로드 완료: 총 {stats.total_calls}회 호출, ${stats.total_cost:.6f}")
                    return stats
        except Exception as e:
            print(f"⚠️ LLM 통계 로드 실패: {e}")
        return UsageStats()

    def _save_stats(self):
        """통계를 파일에 저장합니다"""
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

            data = {
                'total_calls': self.stats.total_calls,
                'successful_calls': self.stats.successful_calls,
                'failed_calls': self.stats.failed_calls,
                'total_input_tokens': self.stats.total_input_tokens,
                'total_output_tokens': self.stats.total_output_tokens,
                'total_cost': self.stats.total_cost,
                'calls_by_model': self.stats.calls_by_model,
                'calls_by_operation': self.stats.calls_by_operation,
                'call_history': self.stats.call_history[-100:],  # 최근 100개만
                'first_call': self.stats.session_start,
                'last_updated': datetime.now().isoformat()
            }

            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ LLM 통계 저장 실패: {e}")

    def estimate_tokens(self, text: str) -> int:
        """텍스트의 토큰 수를 추정합니다 (대략적인 계산)"""
        if not text:
            return 0
        # 한글은 약 1.5글자당 1토큰, 영어는 약 4글자당 1토큰
        # 간단한 휴리스틱 사용
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
        other_chars = len(text) - korean_chars
        estimated = int(korean_chars / 1.5 + other_chars / 4)
        return max(estimated, 1)

    def get_pricing(self, model: str) -> dict:
        """모델의 가격 정보를 반환합니다"""
        return GEMINI_PRICING.get(model, DEFAULT_PRICING)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> tuple:
        """비용을 계산합니다"""
        pricing = self.get_pricing(model)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost, output_cost, input_cost + output_cost

    def track_call(
        self,
        model: str,
        operation: str,
        prompt: str,
        response_text: str,
        latency_ms: float,
        success: bool = True,
        error_message: str = None,
        response_metadata: dict = None
    ) -> APICall:
        """API 호출을 추적합니다"""

        # 토큰 수 계산 (Gemini 응답 메타데이터가 있으면 사용)
        if response_metadata and 'usage_metadata' in response_metadata:
            usage = response_metadata['usage_metadata']
            input_tokens = usage.get('prompt_token_count', self.estimate_tokens(prompt))
            output_tokens = usage.get('candidates_token_count', self.estimate_tokens(response_text))
        else:
            input_tokens = self.estimate_tokens(prompt)
            output_tokens = self.estimate_tokens(response_text) if response_text else 0

        # 비용 계산
        input_cost, output_cost, total_cost = self.calculate_cost(model, input_tokens, output_tokens)

        # 호출 정보 생성
        call = APICall(
            timestamp=datetime.now().isoformat(),
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )

        # 통계 업데이트
        with self._call_lock:
            self.stats.total_calls += 1
            if success:
                self.stats.successful_calls += 1
            else:
                self.stats.failed_calls += 1

            self.stats.total_input_tokens += input_tokens
            self.stats.total_output_tokens += output_tokens
            self.stats.total_cost += total_cost

            # 모델별 통계
            if model not in self.stats.calls_by_model:
                self.stats.calls_by_model[model] = {
                    "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0
                }
            self.stats.calls_by_model[model]["calls"] += 1
            self.stats.calls_by_model[model]["input_tokens"] += input_tokens
            self.stats.calls_by_model[model]["output_tokens"] += output_tokens
            self.stats.calls_by_model[model]["cost"] += total_cost

            # 작업별 통계
            if operation not in self.stats.calls_by_operation:
                self.stats.calls_by_operation[operation] = {
                    "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0
                }
            self.stats.calls_by_operation[operation]["calls"] += 1
            self.stats.calls_by_operation[operation]["input_tokens"] += input_tokens
            self.stats.calls_by_operation[operation]["output_tokens"] += output_tokens
            self.stats.calls_by_operation[operation]["cost"] += total_cost

            # 히스토리 추가 (최근 100개만 유지)
            self.stats.call_history.append({
                "timestamp": call.timestamp,
                "model": call.model,
                "operation": call.operation,
                "input_tokens": call.input_tokens,
                "output_tokens": call.output_tokens,
                "total_cost": call.total_cost,
                "latency_ms": call.latency_ms,
                "success": call.success
            })
            if len(self.stats.call_history) > 100:
                self.stats.call_history = self.stats.call_history[-100:]

            # 파일에 저장
            self._save_stats()

        return call

    def get_stats(self) -> dict:
        """현재 사용량 통계를 반환합니다"""
        with self._call_lock:
            return {
                "session_start": self.stats.session_start,
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "failed_calls": self.stats.failed_calls,
                "total_input_tokens": self.stats.total_input_tokens,
                "total_output_tokens": self.stats.total_output_tokens,
                "total_tokens": self.stats.total_input_tokens + self.stats.total_output_tokens,
                "total_cost_usd": round(self.stats.total_cost, 6),
                "total_cost_krw": round(self.stats.total_cost * 1350, 2),  # 대략적인 환율
                "by_model": dict(self.stats.calls_by_model),
                "by_operation": dict(self.stats.calls_by_operation),
                "recent_calls": self.stats.call_history[-10:]  # 최근 10개 호출
            }

    def reset_stats(self):
        """통계를 초기화합니다"""
        with self._call_lock:
            self.stats = UsageStats()
            # 파일도 초기화
            self._save_stats()
            print("📊 LLM 통계가 초기화되었습니다.")

    def get_summary(self) -> str:
        """사용량 요약을 문자열로 반환합니다"""
        stats = self.get_stats()
        lines = [
            f"📊 LLM 사용량 통계",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"총 호출 수: {stats['total_calls']} (성공: {stats['successful_calls']}, 실패: {stats['failed_calls']})",
            f"총 토큰: {stats['total_tokens']:,} (입력: {stats['total_input_tokens']:,}, 출력: {stats['total_output_tokens']:,})",
            f"총 비용: ${stats['total_cost_usd']:.6f} (약 ₩{stats['total_cost_krw']:.2f})",
            "",
            "📈 모델별 사용량:"
        ]

        for model, data in stats['by_model'].items():
            lines.append(f"  • {model}: {data['calls']}회, {data['input_tokens'] + data['output_tokens']:,} 토큰, ${data['cost']:.6f}")

        lines.append("")
        lines.append("🔧 작업별 사용량:")
        for op, data in stats['by_operation'].items():
            lines.append(f"  • {op}: {data['calls']}회, {data['input_tokens'] + data['output_tokens']:,} 토큰")

        return "\n".join(lines)


# 싱글톤 인스턴스
tracker = LLMTracker()


def track_gemini_call(operation: str):
    """Gemini API 호출을 추적하는 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000

                # 응답에서 메타데이터 추출 시도
                response_metadata = None
                response_text = ""

                if hasattr(result, 'text'):
                    response_text = result.text
                if hasattr(result, '_result'):
                    response_metadata = {'usage_metadata': getattr(result._result, 'usage_metadata', None)}

                # 프롬프트 추출 (args나 kwargs에서)
                prompt = ""
                if args:
                    for arg in args:
                        if isinstance(arg, str):
                            prompt = arg
                            break
                        elif isinstance(arg, list):
                            for item in arg:
                                if isinstance(item, str):
                                    prompt += item + "\n"

                tracker.track_call(
                    model="gemini-2.0-flash",  # 기본값
                    operation=operation,
                    prompt=prompt,
                    response_text=response_text,
                    latency_ms=latency_ms,
                    success=True,
                    response_metadata=response_metadata
                )

                return result
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                tracker.track_call(
                    model="gemini-2.0-flash",
                    operation=operation,
                    prompt="",
                    response_text="",
                    latency_ms=latency_ms,
                    success=False,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator
