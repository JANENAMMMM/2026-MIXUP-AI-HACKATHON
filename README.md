# ✈️ GTA: Global Travel Agent

> **자연어 한 문장으로 완성하는 AI 여행 플래너**
>
> 채팅 한 줄이면 날짜 최적화 · 항공권 조회 · 숙소 선택 · 맛집·명소 큐레이션 · 동선 최적화 · 최종 일정표까지 자동 설계됩니다.

---

## 🏆 2026 MIXUP AI HACKATHON

본 프로젝트는 **BITAmin, Prometheus, Tobig’s가 주최**하고 **Upstage(업스테이지)가 주관**하는 [2026 MIXUP AI HACKATHON] 출품작입니다. (대회 기간: 2026.05.22 ~ 05.23, 경기창조경제혁신센터 판교 창업존)

### 💡 프로젝트 시작 배경 (Why?)
최근 단순 프로세스 자동화를 넘어, 다양한 API와 외부 데이터를 기반으로 스스로 판단하고 작업을 수행하는 **통합형 AI Agent** 시스템으로의 패러다임 전환이 빠르게 이루어지고 있습니다. 기존의 단일 기능 중심 서비스로는 복잡한 여행 계획의 변수들을 처리하기 어렵다는 한계가 있었습니다.
이에 우리는 **Upstage의 Solar Pro3 API**를 핵심 추론 엔진으로 삼아, 사용자의 복잡한 자연어 요구사항(예방, 날짜 미정, 편의 시설 등)을 분석하고 외부 API(항공, 숙박, 날씨 등)를 연동 및 제어하여 최적의 여행 일정을 도출하는 **End-to-End 지능형 통합 여행 에이전트**를 기획하게 되었습니다.

### 🚀 1일(무박 2일) 완성 MVP
본 서비스는 무박 2일이라는 한정된 시간(실제 개발 기간 약 1일 이내) 내에 기획부터 문제 정의, API 연동, Agent 의사결정 로직 설계 및 프론트엔드 시연까지 완수해 낸 **MVP (Minimum Viable Product, 최소 기능 제품)**입니다. 짧은 기간이지만 실제 환경에서 동작하며 실효성을 증명하는 데 초점을 맞추어 구현되었습니다.

---

## 🤝 팀원 소개

| 이름(가나다순) | 학교 | 전공 |
|------|------|------|
| **김 천 지** | 상명대학교 | 컴퓨터과학전공 |
| **남 재 은** | 이화여자대학교 | 인공지능대학 데이터사이언스학과 |
| **노 희 윤** | 경희대학교 | 소프트웨어융합학과 |
| **이 지 원** | 덕성여자대학교 | 디지털소프트웨어공학부 |

---

## 💻 DEMO (서비스 시연)

### 1. 프롬프트 입력 및 의도 추출 (Intent Router)
<img width="1200" height="722" alt="1_의도분석추출" src="https://github.com/user-attachments/assets/fc1ae754-bfc9-49f3-b72f-046cb67c5180" />

사용자의 자연어 입력 한 줄을 `intent_router` 노드가 분석하여 사용자의 핵심 의도를 추출합니다. 이때 예산, 여행 인원 등 플래닝에 필수적인 정보가 누락되었을 경우 에이전트가 역으로 사용자에게 질문하여 필요한 데이터를 수집합니다.

### 2. 비행편·기후 분석을 통한 최적 날짜 추천 및 숙소 선호 파악
<img width="1200" height="722" alt="2_휴먼인더루프" src="https://github.com/user-attachments/assets/007699de-2506-4980-ac32-38aaf76b4a5a" />

기상 데이터(Open-Meteo)와 실시간 항공권 검색 결과를 교차 분석(`date_compute` 노드)하여, 가격과 날씨 점수가 가장 좋은 최적의 날짜 후보들을 추천합니다. 사용자가 날짜를 확정(HITL 개입)하면, 이어서 원하는 숙소 유형과 편의시설 선호도를 추가로 입력받습니다.

### 3. 맞춤 숙소 추천 및 사용자 선택 반영
<img width="1200" height="722" alt="3_추천결과" src="https://github.com/user-attachments/assets/40e9543b-c9bb-41a5-ba79-94326f0cb47c" />

수집된 총 예산에서 왕복 항공권 비용을 차감한 잔여 예산과 승객 수, 그리고 방금 입력받은 숙소 선호 조건을 바탕으로 `hotel_compute` 노드가 실시간으로 숙소를 검색합니다. 사용자는 제시된 맞춤형 호텔 후보 호텔 카드들 중에서 하나를 직접 선택하여 여정을 구체화합니다.

### 4. 동선 최적화 및 상황별 최종 일정표 생성
<img width="1200" height="722" alt="4_최종 결과" src="https://github.com/user-attachments/assets/80761fe4-40de-41a4-86f8-1cfa1400627d" />

`place` 노드가 맛집/명소를 탐색 후 TSP 근사 알고리즘으로 동선을 최적화하면, 최종적으로 `synthesizer` 노드가 완성된 마크다운 일정표를 제공합니다. 우천 시 실내 여행 일정으로 경로를 유연하게 대체하는 등, 날씨 컨텍스트까지 반영한 에이전트의 상황 대처 능력을 반영하였습니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [Agent Pipeline 상세](#3-agent-pipeline-상세)
4. [Human-in-the-Loop (HITL)](#4-human-in-the-loop-hitl)
5. [기술 스택](#5-기술-스택)
6. [디렉터리 구조](#6-디렉터리-구조)
7. [환경 변수](#7-환경-변수)
8. [실행 방법](#8-실행-방법)
9. [API 명세](#9-api-명세)

---

## 1. 프로젝트 개요

**Global Travel Agent**는 사용자의 자연어 입력 한 문장을 LangGraph 멀티에이전트 파이프라인으로 처리해 완성형 여행 일정을 생성하는 AI 서비스입니다.

### 핵심 특징

| 기능 | 설명 |
|------|------|
| **자연어 이해** | "7월 오사카 3박, 예산 150만원" 같은 자유 형식 입력 처리 |
| **날짜 최적화** | 날짜 미정 시 항공권 가격 + 날씨 점수 기반 최적 일정 TOP 3 추천 |
| **항공권 조회** | SerpAPI Google Flights로 실시간 최저가 항공편 탐색 |
| **날씨 분석** | Open-Meteo API로 해당 기간 날씨 예보 / 과거 통계 제공 |
| **숙소 검색** | SerpAPI Google Hotels로 예산·등급·편의시설 조건 반영 실시간 검색 |
| **장소 큐레이션** | Google Places API + Naver Local API 병렬 호출 후 LLM 큐레이션 |
| **동선 최적화** | 좌표 기반 TSP 근사 알고리즘으로 효율적인 방문 순서 계산 |
| **일정 생성** | Solar Pro3 LLM이 GFM 마크다운 표 형식의 최종 여행 일정 생성 |
| **일정 수정** | 피드백 기반 Synthesizer 재실행 (최대 3회) |

---

## 2. 시스템 아키텍처

<img width="1167" height="554" alt="흐름도" src="https://github.com/user-attachments/assets/9fc9a49f-b223-4cc9-84d8-8ab9df0ab5af" />


---

## 3. Agent Pipeline 상세

### 노드 구성 (9개)

<img width="188" height="1027" alt="그래프구조" src="https://github.com/user-attachments/assets/deaa04c9-2674-4683-8639-13292b41e799" />


이 AI 에이전트는 LangGraph 환경에서 작동하며, 목적에 따라 다양한 노드(Node) 및 엣지(Edge)로 구성되어 있습니다. `__start__`에서 시작하여 각 노드를 순차적으로 거치며, 특정 조건 혹은 사용자 개입(HITL) 필요 여부에 따라 `date_select`나 `hotel_select`와 같은 노드로 진입하거나 이를 건너뛰는(bypass/점선 엣지) 형태의 워크플로우를 가집니다. 이를 통해 유연하고 최적화된 과정을 거쳐 최종 `__end__`에 도달하게 됩니다.

### 각 노드 설명

| # | 노드 | 역할 | 외부 API |
|---|------|------|---------|
| 1 | **intent_router** | 자연어 → `TravelIntent` 파싱 (목적지, 날짜, 예산, 인원 등) | Solar Pro3 LLM |
| 2 | **date_compute** | 항공권 + 날씨 교차 분석 (3가지 분기 처리) | Naver Flights GraphQL · SerpAPI Flights · Open-Meteo |
| 3 | **date_select** | 사용자에게 날짜 후보 제시 후 선택 대기 (후보 없으면 자동 스킵) | — (interrupt) |
| 4 | **weather** | 날씨 보완 조회 (date_compute에서 이미 계산됐으면 캐시 재사용) | Open-Meteo |
| 5 | **hotel_prefs** | 정렬 기준·등급·편의시설 등 숙소 조건 수집 | — (interrupt) |
| 6 | **hotel_compute** | 예산·선호 조건 반영 실시간 호텔 검색 | SerpAPI Hotels |
| 7 | **hotel_select** | 호텔 후보 카드 제시 후 선택 대기 | — (interrupt) |
| 8 | **place** | 맛집·명소 병렬 검색 → LLM 큐레이션 → 좌표 기반 동선 최적화 | Google Places + Naver Local |
| 9 | **synthesizer** | 수집된 모든 정보로 GFM 마크다운 일정표 생성 | Solar Pro3 LLM |

### date_compute 분기 상세

```
date_compute
  ├─ 국내선 / IATA 코드 없음
  │    └→ Open-Meteo 날씨만으로 후보 생성 (항공 조회 생략)
  │
  ├─ 날짜 확정 (date_fixed=True)
  │    └→ SerpAPI Google Flights로 해당 날짜 항공편 직접 조회
  │         + Open-Meteo 날씨 계산 → 1개 후보 반환
  │
  └─ 날짜 미정 (date_fixed=False)
       └→ Naver Flights GraphQL (primary)으로 월별 최저가 최대 50건 수집
            → SERPAPI Google Flights (fallback, 시각 정보 보완)
            → 가격·경유·출발시간 사전 점수 산출 → 상위 20건 선별
            → Open-Meteo 날씨 병렬 조회 (ThreadPoolExecutor, 최대 8개 동시)
            → 항공 점수 + 날씨 점수 종합 → TOP 10 후보 반환
```

**weather 노드는 중복 조회를 하지 않습니다.** `date_compute`가 이미 날씨를 state에 저장했으면 weather 노드는 재사용하고, 날씨가 없는 경우에만 Open-Meteo를 새로 호출합니다.

### 예산 흐름

```
총 예산
  ─ 항공비 (왕복, 실시간 조회)
  ─ 숙박비 (야간 × 1박 상한 이내)
  = 잔여 예산 (식비·관광 등)
```

---

## 4. Human-in-the-Loop (HITL)

LangGraph의 `interrupt()` + `Command(resume=...)` 패턴으로 3단계 사용자 개입을 구현합니다.

### HITL 흐름

```
[날짜 선택]        → 최적 날짜 TOP 3 카드 → 사용자 선택 → 재개
[숙소 조건 설정]   → 등급/편의시설 필터 UI → 사용자 설정 → 재개
[숙소 선택]        → 호텔 후보 카드 (이미지·가격·별점) → 사용자 선택 → 재개 (SSE 스트리밍)
```

### 일정 피드백 루프 (최대 3회)

완성된 일정에 자연어로 수정 요청을 보내면 Synthesizer만 재실행합니다.

```
사용자 피드백 입력
  └→ POST /api/plan/refine
       └→ LangGraph thread state 읽기
            └→ synthesizer 단독 재실행 (피드백 반영)
                 └→ 수정된 일정 인라인 교체
```

- 1차 수정: 파란색 배지
- 2차 수정: 주황색 배지
- 3차 수정: 초록색 배지

### 실시간 진행 스트리밍 (SSE)

숙소 선택 이후 place·synthesizer 노드 진행 상황을 Server-Sent Events로 실시간 전달합니다.

```
hotel_select 완료
  └→ POST /api/plan/resume/stream
       └→ background thread에서 LangGraph 실행
            └→ progress.emit() → Queue → SSE → 프론트엔드 파이프라인 로그
```

---

## 5. 기술 스택

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

## 6. 디렉터리 구조

```
.
├── api/                          # FastAPI 백엔드
│   ├── main.py                   # FastAPI 앱 + CORS 설정
│   ├── schemas.py                # Pydantic 요청/응답 모델
│   └── routes/
│       └── plan.py               # /api/plan/* 라우터 (start·resume·stream·refine)
│
├── src/
│   ├── agent/
│   │   ├── graph.py              # LangGraph 9-노드 그래프 빌드
│   │   ├── state.py              # AgentState TypedDict
│   │   ├── llm.py                # LLM 팩토리 (Upstage Solar)
│   │   ├── progress.py           # SSE 진행 메시지 발행 (thread-local)
│   │   └── nodes/
│   │       ├── intent_router.py  # [1] 자연어 파싱
│   │       ├── date_optimizer.py # [2][3] 날짜 최적화 + 선택
│   │       ├── weather_node.py   # [4] 날씨 분석
│   │       ├── stay_node.py      # [5][6][7] 숙소 조건·검색·선택
│   │       ├── place_node.py     # [8] 장소 큐레이션 + 동선 최적화
│   │       └── synthesizer_node.py # [9] 일정 생성 (피드백 반영)
│   │
│   ├── cheapest_date/            # 항공권 최저가 날짜 탐색
│   │   ├── flight_crawler.py     # SerpAPI Flights 래퍼
│   │   ├── iata.py               # 도시 → IATA 코드 변환
│   │   └── models.py
│   │
│   ├── hotel/                    # 호텔 검색
│   │   ├── search.py             # SerpAPI Hotels 래퍼
│   │   └── models.py             # HotelSearchRequest / Hotel / HotelSearchResult
│   │
│   ├── tourist/                  # 장소 검색
│   │   ├── google_places.py      # Google Places API
│   │   └── naver_local.py        # Naver Local Search API
│   │
│   ├── weather/                  # 날씨 데이터
│   │   ├── forecast.py           # Open-Meteo 예보 / 과거 통계
│   │   └── geocoding.py          # 도시명 → 좌표 (Nominatim)
│   │
│   └── transport/                # 교통 (항공 모델)
│
├── lovable/                      # TanStack Start 프론트엔드
│   └── src/
│       ├── routes/
│       │   ├── __root.tsx        # 루트 레이아웃 + 에러 바운더리
│       │   └── index.tsx         # 메인 페이지
│       ├── components/
│       │   └── travel/
│       │       ├── TravelPlannerApp.tsx  # 메인 앱 컴포넌트
│       │       └── MarkdownContent.tsx  # GFM 마크다운 렌더러
│       └── lib/
│           ├── api.ts            # 백엔드 API 클라이언트 (SSE 포함)
│           └── travel/
│               ├── types.ts      # 타입 정의
│               └── mockData.ts   # 예시 프롬프트 · 옵션 목록
│
├── main.py                       # FastAPI 서버 진입점
├── run_cli.py                    # CLI 테스트 실행기
└── pyproject.toml                # Python 의존성
```

---

## 7. 환경 변수

프로젝트 루트에 `.env` 파일을 생성합니다.

```dotenv
# LLM (필수)
UPSTAGE_API_KEY=your_upstage_api_key

# 외부 API (필수)
SERPAPI_KEY=your_serpapi_key
GOOGLE_PLACES_API_KEY=your_google_places_key

# Naver Local Search (선택 — 국내 여행 시 맛집 검색 품질 향상)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# LangSmith 추적 (선택)
LANGSMITH_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=global-travel-agent
```

> Open-Meteo는 API 키 없이 사용 가능합니다.

---

## 8. 실행 방법

### 백엔드

```bash
# 의존성 설치 (uv 권장)
uv sync

# 또는 pip
pip install -e .

# 서버 실행
uvicorn main:app --reload --port 8000
```

### 프론트엔드

```bash
cd lovable

# 의존성 설치
npm install

# 개발 서버
npm run dev
# → http://localhost:3000

# 프로덕션 빌드
npm run build
```

### CLI 테스트

백엔드 없이 에이전트를 터미널에서 직접 실행합니다.

```bash
python run_cli.py
# 또는
python run_cli.py "오사카 7월 초 3박4일, 혼자, 예산 100만원"
```

### LangGraph 그래프 이미지 생성

```bash
python -m src.agent.graph --output graph.png
```

---

## 9. API 명세

### `POST /api/plan/start`

여행 계획 파이프라인을 시작합니다. 첫 interrupt(날짜 또는 호텔 조건 선택)에서 응답을 반환합니다.

**Request**
```json
{
  "message": "오사카 7월 초 3박, 예산 150만원",
  "budget": "150만원",
  "people": "2명"
}
```

**Response** (`phase: "date_selection"` 예시)
```json
{
  "thread_id": "uuid",
  "phase": "date_selection",
  "question": "여행 날짜를 선택해주세요:",
  "candidates": [
    { "check_in": "2026-07-01", "check_out": "2026-07-04",
      "flight_price": 228000, "weather_summary": "맑음 28°C",
      "score": 87, "reason": "항공가 최저 + 쾌청한 날씨" }
  ]
}
```

---

### `POST /api/plan/resume`

interrupt에서 사용자 선택을 전달하고 다음 단계로 재개합니다.

**Request**
```json
{ "thread_id": "uuid", "choice": "1" }
```

**Response**: `StartPlanResponse` — 다음 interrupt 또는 완료 결과

---

### `POST /api/plan/resume/stream`

호텔 선택 이후 place·synthesizer 단계를 SSE로 스트리밍합니다.

**SSE 이벤트 형식**
```
data: {"type": "progress", "message": "🔍 장소 검색 중 — 오사카"}
data: {"type": "progress", "message": "✅ 동선 최적화 완료"}
data: {"type": "final", "thread_id": "...", "phase": "done", "result": {...}}
data: [DONE]
```

---

### `POST /api/plan/refine`

기존 thread의 synthesizer를 피드백과 함께 재실행합니다 (최대 3회).

**Request**
```json
{ "thread_id": "uuid", "feedback": "2일차가 너무 빡빡해, 명소 하나 빼줘" }
```

**Response**: 수정된 `PlanResponse` (final_report 포함)

---

### `GET /health`

```json
{ "status": "ok" }
```

