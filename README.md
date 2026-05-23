# ✈️ 2026 MIXUP AI HACKATHON: AI 기반 여행 플래너

연합동아리 비타민, 프로메테우스, 투빅스 주최 해커톤 프로젝트입니다.
본 서비스는 사용자의 여행 의도를 파악하고 항공권, 숙박, 관광지, 날씨 등 다양한 정보를 통합 분석하여 최적의 여행 플랜과 동선을 제안해 주는 **AI 기반 지능형 여행 플래너 에이전트**입니다.

## 🛠 Tech Stack (기술 스택)

해당 프로젝트는 **Python/FastAPI** 기반의 백엔드(AI Agent 특화)와 **React/TanStack** 기반의 프론트엔드로 구성되어 있습니다.

### 🧠 AI & Agent (Backend Core)

- **LLM Provider**: `Upstage` (`langchain-upstage`) - 한국어 처리에 특화된 Solar LLM 기반 추론
- **Agent Framework**: `LangGraph` (`langgraph`) - 복잡한 의사결정(Intent Router, 최적화 노드 등) 및 순환(Cyclic) 그래프 형태의 워크플로우 구축
- **LLM Orchestration**: `LangChain Core` (`langchain-core`) - 상태(State) 관리 및 도구(Tool) 바인딩
- **Observability**: `LangSmith` (`langsmith`) - LLM 로그 추적 및 프롬프트 최적화

### ⚙️ Backend (API Server)

- **Language**: `Python 3.10+`
- **Web Framework**: `FastAPI` (`fastapi`) - 높은 속도와 비동기 처리에 강력한 API 서버
- **ASGI Server**: `Uvicorn` (`uvicorn[standard]`)
- **Package / Env Manager**: `uv` (빠르고 안정적인 의존성 및 가상환경 관리)
- **HTTP Client**: `requests` - 서드파티 API 통신
- **Streaming**: `sse-starlette` - AI 응답의 실시간 스트리밍(SSE) 처리

### 🌐 Frontend (Web Application)

- **Framework**: `React 19`, `TypeScript`
- **Meta-Framework & Routing**: `TanStack Start`, `TanStack Router` - SSR/CSR 기반의 강력하고 타입 안정성이 보장된 라우팅
- **State Management**: `TanStack Query` (React Query) - 서버 데이터 페칭 및 캐싱
- **Build Tool**: `Vite` (+ Cloudflare Vite Plugin)
- **Styling**: `Tailwind CSS v4`
- **UI Components**: `shadcn/ui` (under the hood: `Radix UI`) - 유연하고 접근성 높은 UI 컴포넌트 사용
- **Icons & Visualization**: `Lucide React` (아이콘), `Recharts` (차트 데이터 시각화)
- **Markdown Rendering**: `react-markdown`, `remark-gfm` - AI가 생성한 마크다운 형태의 여행 계획 렌더링

### 🔌 External APIs & Tools

- **날씨 (Weather)**: `Open-Meteo API` (과거 기후 리서치 및 장단기 예보, API 키 불필요)
- **장소 및 명소 (Tourist)**:
  - `Google Places API` (해외 식당/카페/관광명소 검색)
  - `Naver Local API` (국내 장소 검색 최적화)
- **항공/교통 (Transport)**: `IATA API` 활용 최저가 항공권 탐색 및 운항 정보 데이터
- **숙박 (Hotel)**: 내부 호텔/숙소 검색 연동

---

## 📂 Project Structure (프로젝트 구조)

```text
2026-MIXUP-AI-HACKATHON/
│
├── api/                   # FastAPI 엔드포인트 및 라우팅 (API 진입점)
│   ├── main.py            # API 서버 메인 실행 파일
│   └── routes/            # 실질적인 데이터 응답 및 스트리밍 처리 (plan.py 등)
│
├── src/                   # 백엔드 핵심 비즈니스 로직 및 AI 에이전트 소스
│   ├── agent/             # LangGraph 기반 에이전트 구성 (graph.py, state.py, llm.py)
│   │   └── nodes/         # 라우팅(Intent), 날씨, 장소, 숙박, 내용 합성 등 Graph Node 모음
│   ├── tools/             # 에이전트가 활용하는 Tools (관광, 호텔, 최저가, 날씨, 교통 등)
│   ├── tourist/           # 구글/네이버 등 관광지 API 연동 모듈
│   ├── weather/           # Open-Meteo API 기반 날씨 조회 로직
│   ├── transport/         # 교통 및 항공권 운항 정보 조회
│   ├── cheapest_date/     # 최저가 항공권(IATA) 날짜/가격 스크래퍼
│   └── hotel/             # 호텔 및 숙박 검색 로직
│
├── lovable/               # Frontend 웹 애플리케이션 (React + TanStack Start)
│   ├── src/               # 프론트엔드 라우터 및 UI 컴포넌트 (router.tsx, UI components 등)
│   ├── package.json       # 프론트엔드 의존성 (Vite, Tailwind, Radix UI 등)
│   └── vite.config.ts     # Vite 환경 설정
│
├── pyproject.toml         # 파이썬 의존성 및 프로젝트 설정 (uv 호환)
└── README.md              # 본 문서
```

---

## 🚀 Getting Started (설치 및 실행 방법)

### 1. 백엔드 (Backend) 설정

프로젝트 루트에서 `uv` 패키지 매니저를 통해 필요한 Python 환경을 구축합니다.

```bash
# uv 설치 (이미 설치되어 있을 경우 생략)
# Windows:  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치 및 가상환경 셋업
uv sync

# API 서버 실행 (보통 FastAPI 구동)
uv run uvicorn api.main:app --reload
```

_(루트에 제공된 `run_cli.py` 또는 `main.py`를 활용해 CLI로 직접 날씨/에이전트를 테스트 할 수도 있습니다.)_

### 2. 프론트엔드 (Frontend) 설정

`lovable` 디렉토리로 이동하여 의존성을 설치하고 개발 서버를 시작합니다.

```bash
# lovable 폴더로 진입
cd lovable

# npm을 통한 패키지 설치
npm install

# 프론트엔드 개발 서버 실행
npm run dev
```

---

_본 프로젝트는 [2026 MIXUP AI HACKATHON] 제출용으로 구현되었습니다._
