# Real Quiz - Math Image Parser with Variant Question Generation

## Project Overview
수학 시험 문항 이미지를 분석하고 변형 문제를 자동 생성하는 웹 애플리케이션

## Tech Stack

### Backend (Flask)
- **Framework**: Flask with CORS
- **AI**: Google Gemini API (gemini-2.5-pro for image analysis)
- **Language**: Python 3.x

### Frontend (Next.js)
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Math Rendering**: KaTeX

## Project Structure

```
real-quiz/
├── flask/                        # Flask backend
│   ├── app.py                    # Main Flask application (~1700 lines)
│   ├── llm_tracker.py            # LLM API usage tracking with cost calculation
│   ├── generate_variants.py      # Variant question generation logic
│   ├── generate_exam.py          # Exam generation utilities
│   ├── draw_geometry.py          # Geometry drawing utilities
│   ├── analyze_question.py       # Question analysis utilities
│   ├── requirements.txt          # Python dependencies
│   ├── config/
│   │   └── system_prompt.txt     # Gemini system prompt configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── prompts.py            # Prompt management API
│   │   └── llm_stats.py          # LLM statistics API
│   └── utils/
│       ├── __init__.py
│       ├── json_parser.py        # JSON parsing with LaTeX escape handling
│       ├── image.py              # Image processing (crop by bounding box)
│       └── llm.py                # LLM error recovery functions
├── client/                       # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Main page (~2900 lines, single-page app)
│   │   └── globals.css
│   ├── package.json
│   └── tsconfig.json
├── .env                          # Environment variables (not in git)
├── .env.example                  # Environment template
├── run-dev.sh                    # Development startup script
├── Dockerfile                    # Docker configuration (full stack)
├── Dockerfile.backend            # Backend-only Docker
├── docker-compose.yml            # Docker Compose setup
└── docker-entrypoint.sh          # Docker entrypoint script
```

## Environment Variables

```bash
# .env
GEMINI_API_KEY=<your-gemini-api-key>
SERVER_URL=http://localhost:4001
PORT=4001
GEN_DATA_PATH=~/gen-data  # External data storage path
```

## Data Storage (GEN_DATA_PATH)

생성 데이터는 프로젝트 외부에 저장됨 (`~/gen-data/`):
```
~/gen-data/
├── flask_uploads/images/     # Uploaded exam images
├── data/
│   ├── sessions/             # Analysis session data (JSON)
│   └── llm_stats.json        # LLM usage statistics
└── variants_output/          # Generated variant questions
```

## Key APIs

### Image Analysis
- `POST /analyze` - Analyze exam image with Gemini Vision
- `POST /analyze-manual` - Analyze with custom prompts

### Session Management
- `GET /sessions` - List all sessions
- `POST /sessions` - Create new session
- `GET /sessions/<id>` - Get session details
- `DELETE /sessions/<id>` - Delete session

### Variant Generation
- `POST /generate-variants` - Generate variant questions
- `GET /variant-progress/<id>` - Get generation progress
- `GET /variants/<session_id>` - List variants for session

### Prompts
- `GET /prompts` - Get current prompts
- `POST /prompts` - Save prompts
- `POST /prompts/reset` - Reset to defaults

### Statistics
- `GET /llm-stats` - Get LLM usage statistics
- `POST /llm-stats/reset` - Reset statistics
- `GET /llm-stats/summary` - Get text summary

## Development

### Quick Start (Both servers)
```bash
./run-dev.sh
```

### Start Backend Only
```bash
cd flask
python app.py
# Server runs on http://localhost:4001
```

### Start Frontend Only
```bash
cd client
npm run dev
# Client runs on http://localhost:3000
```

### Docker
```bash
docker-compose up
```

## Git Information
- **Repository**: https://gitlab.aidtclass.com/axlabs/axlabs-home.git
- **Branch**: feature/demo
- **Remote**: origin

## Key Features
1. **Image Analysis**: Gemini Vision으로 시험 문항 이미지 분석
2. **LaTeX Support**: 수식을 LaTeX로 변환하여 저장
3. **Bounding Box**: 각 문항의 위치 정보 추출 및 이미지 크롭
4. **Variant Generation**: AI 기반 변형 문제 자동 생성
5. **LLM Tracking**: API 사용량 및 비용 추적
6. **Session Management**: 분석 세션 관리 및 저장
7. **Analysis Process**: 저학년 문장제 문제의 3단계 분석 표시

## Notes
- Frontend는 단일 페이지 앱 (page.tsx ~2900 lines)
- 한글 주석 및 메시지 사용
- Gemini API 토큰 비용 추적 지원

## Recent Changes (2025-12-07)

### 프로젝트 구조 변경
- Flask 소스 파일들을 `flask/` 폴더로 이동
- `run-dev.sh` 개발 서버 실행 스크립트 추가
- Docker 설정 파일 업데이트

### 변형문제 해설 간결화
- 중언부언 제거, `[풀이] → 사용 개념 → 수식` 형식으로 변경
- generate_variants.py 프롬프트 수정

### 크롭된 이미지 표시 기능
- 여러 문제 이미지 분석 시 각 문제별 크롭 이미지 저장 (`cropped.{ext}`)
- bounding_box 없을 시 균등 분할 fallback 로직

### 분석 프로세스 UI
- 저학년 문장제 문제 3단계 분석 표시 (수식 변환 → 풀이 → 문맥 복원)
- LaTeX 렌더링 지원
