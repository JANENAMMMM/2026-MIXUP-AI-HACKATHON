# 🌤 Weather API - 전세계 날씨 조회

Open-Meteo API를 사용해 도시명과 날짜를 입력하면 날씨 정보를 출력합니다.  
**API 키 불필요 · 완전 무료 · 한글 도시명 지원**

## 날짜 범위별 지원

| 날짜 범위 | API | 특징 |
|---|---|---|
| 과거 | ERA5 Historical Archive | 1940년부터 조회 가능 |
| 오늘 ~ +16일 | Forecast API | 시간별/일별 예보 |
| +17일 ~ +9개월 | Seasonal Forecast API | ECMWF SEAS5 앙상블 평균 |

## 설치

[uv](https://docs.astral.sh/uv/) 사용 (pip 대신 권장)

```bash
# uv가 없으면 먼저 설치
# Windows:  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치 (.venv 자동 생성)
uv sync
```

## 사용법

### 커맨드라인

```bash
# 오늘 날씨
uv run python main.py 서울 today

# 특정 날짜
uv run python main.py "New York" 2026-07-01
uv run python main.py 파리 2026-09-15

# 기본 예시 (여러 도시 한번에)
uv run python main.py
```

### 코드에서 import

```python
from weather import get_weather

get_weather('서울', 'today')           # 오늘
get_weather('도쿄', '2026-06-10')      # 단기 예보
get_weather('런던', '2026-10-01')      # 시즌 예보
```

## 출력 항목

- 날씨 상태 (WMO 코드 기반)
- 기온 (최고 / 최저 / 평균 / 체감)
- 강수량 (비 · 눈 · 강수 시간 · 강수 확률)
- 바람 (속도 · 돌풍 · 방향)
- UV 지수 · 일사량 · 일조시간
- 일출 · 일몰

## 프로젝트 구조

```
├── main.py               # 실행 진입점
├── pyproject.toml        # 프로젝트 메타데이터 및 의존성 (uv)
├── uv.lock               # 의존성 버전 고정 (커밋 대상)
├── .env.example
└── weather/              # 날씨 패키지
    ├── __init__.py       # get_weather() 메인 함수
    ├── config.py         # API URL, 변수 목록, WMO 코드
    ├── geocoding.py      # 도시명 → 좌표 (Nominatim)
    ├── forecast.py       # 날씨 API 호출 (예보 / 과거 / 시즌)
    └── display.py        # 콘솔 출력 포맷
```

## 사용 API

- **[Open-Meteo](https://open-meteo.com/)** - 날씨 데이터 (무료, API 키 불필요)
- **[Nominatim / OpenStreetMap](https://nominatim.org/)** - 지오코딩 (무료, API 키 불필요)
