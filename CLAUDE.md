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
├── app.py                    # Main Flask application (~1900 lines)
├── llm_tracker.py            # LLM API usage tracking with cost calculation
├── generate_variants.py      # Variant question generation logic
├── generate_exam.py          # Exam generation utilities
├── draw_geometry.py          # Geometry drawing utilities
├── analyze_question.py       # Question analysis utilities
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (not in git)
├── .env.example              # Environment template
├── config/
│   └── system_prompt.txt     # Gemini system prompt configuration
├── routes/
│   ├── __init__.py
│   ├── prompts.py            # Prompt management API
│   └── llm_stats.py          # LLM statistics API
├── utils/
│   ├── __init__.py
│   ├── json_parser.py        # JSON parsing with LaTeX escape handling
│   ├── image.py              # Image processing (crop by bounding box)
│   └── llm.py                # LLM error recovery functions
├── client/                   # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx          # Main page (~103KB, single-page app)
│   │   └── globals.css
│   ├── package.json
│   └── tsconfig.json
├── Dockerfile                # Docker configuration
├── Dockerfile.backend        # Backend-only Docker
├── docker-compose.yml        # Docker Compose setup
└── docker-entrypoint.sh      # Docker entrypoint script
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

### Start Backend
```bash
python app.py
# Server runs on http://localhost:4001
```

### Start Frontend
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
3. **Bounding Box**: 각 문항의 위치 정보 추출
4. **Variant Generation**: AI 기반 변형 문제 자동 생성
5. **LLM Tracking**: API 사용량 및 비용 추적
6. **Session Management**: 분석 세션 관리 및 저장

## Notes
- Frontend는 단일 페이지 앱 (page.tsx ~103KB)
- 한글 주석 및 메시지 사용
- Gemini API 토큰 비용 추적 지원

## Recent Changes (2025-12-05)

### 크롭된 이미지 표시 기능
여러 문제가 포함된 이미지 분석 시, 각 문제별로 크롭된 이미지를 표시하는 기능 구현:

**Backend (app.py:751-760):**
- `bounding_box`와 `len(questions) > 1` 조건이 모두 만족할 때만 이미지 크롭
- 크롭된 경우에만 `question['cropped_image_url']` 필드 추가
- 단일 문제 이미지는 크롭하지 않고 원본 그대로 사용

**Frontend (client/app/page.tsx):**
- `QuestionData` 인터페이스에 `cropped_image_url?: string` 필드 추가
- `QuestionCard` 컴포넌트에 크롭된 이미지 표시 UI 추가 (보라색 테마)
- `question.cropped_image_url`이 있을 때만 "원본 이미지" 섹션 표시

### 서버 상태
- Backend: http://localhost:4001 (Flask, 디버그 모드)
- Frontend: http://localhost:3000 (Next.js)

### 미해결 이슈
- **크롭된 이미지 표시 안됨**: 여러 문제 이미지 분석 시 크롭된 이미지가 프론트엔드에 표시되지 않는 문제 - 추후 디버깅 필요
