# API 모듈 문서

여행 플래닝에 필요한 4가지 API 모듈을 제공합니다.  
모든 모듈은 `src/` 패키지 아래에 위치하며, 각 모듈에 `models.py`가 있어 입출력 타입을 명확히 정의합니다.

---

## 환경 변수 설정 (`.env`)

```
SERPAPI_KEY=...          # 호텔, 항공, 대중교통 (SerpApi)
GOOGLE_API_KEY=...       # 관광지 검색 (Google Places)
NAVER_CLIENT_ID=...      # 네이버 지역 검색
NAVER_CLIENT_SECRET=...  # 네이버 지역 검색
```

---

## 실행

```bash
uv run python main.py weather 서울 today
uv run python main.py hotel "Seoul hotels" 2026-06-01 2026-06-03
uv run python main.py tourist "Tokyo Shibuya restaurants"
uv run python main.py naver "해운대 횟집"
uv run python main.py flight ICN NRT 2026-06-01
uv run python main.py transit 서울역 부산역
```

---

## 모듈별 API 레퍼런스

---

### 1. 날씨 — `src/weather`

**외부 API**: [Open-Meteo](https://open-meteo.com/) (무료, API 키 불필요)

#### 함수

```python
from src.weather import get_weather

result: WeatherResult | None = get_weather(city: str, date_str: str)
```

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `city` | `str` | 도시명 (한글/영문, 예: `"서울"`, `"Tokyo"`) |
| `date_str` | `str` | `"today"` 또는 `"YYYY-MM-DD"` |

날짜 범위에 따라 API를 자동 선택:

| 날짜 범위 | 사용 API | 특징 |
|-----------|----------|------|
| 과거 | ERA5 Historical Archive | 1940년부터 조회 |
| 오늘 ~ +16일 | Forecast API | 단기 예보 |
| +17 ~ +270일 | Seasonal API | ECMWF SEAS5 앙상블 평균 |
| +270일 초과 | — | `None` 반환 |

#### 모델 (`src/weather/models.py`)

```python
@dataclass
class WeatherRequest:
    city: str       # 도시명
    date: str       # 'today' 또는 'YYYY-MM-DD'

@dataclass
class DailyWeather:
    date: str
    weather_code: int | None            # WMO 날씨 코드
    temp_max: float | None              # 최고 기온 (°C)
    temp_min: float | None              # 최저 기온 (°C)
    temp_mean: float | None             # 평균 기온 (°C)
    apparent_temp_max: float | None     # 최고 체감 기온 (°C)
    apparent_temp_min: float | None     # 최저 체감 기온 (°C)
    precipitation_sum: float | None     # 총 강수량 (mm)
    rain_sum: float | None              # 강우량 (mm)
    snowfall_sum: float | None          # 적설량 (cm)
    precipitation_hours: float | None
    precipitation_probability_max: float | None  # 최대 강수 확률 (%)
    windspeed_max: float | None         # 최대 풍속 (km/h)
    windgusts_max: float | None         # 최대 돌풍 (km/h)
    wind_direction: float | None        # 풍향 (°)
    uv_index_max: float | None
    shortwave_radiation_sum: float | None  # 일사량 (MJ/m²)
    sunshine_duration: float | None     # 일조 시간 (초)
    daylight_duration: float | None     # 낮 길이 (초)
    sunrise: str | None                 # ISO 시각
    sunset: str | None

@dataclass
class WeatherResult:
    city: str
    country: str
    lat: float
    lon: float
    date: str
    delta_days: int         # 오늘 기준 +/- 일수
    source: str             # 데이터 출처 레이블
    daily: DailyWeather | None
```

#### 사용 예시

```python
from dotenv import load_dotenv
load_dotenv()

from src.weather import get_weather

result = get_weather("서울", "today")
if result and result.daily:
    print(f"최고 기온: {result.daily.temp_max}°C")
    print(f"강수 확률: {result.daily.precipitation_probability_max}%")
```

---

### 2. 호텔 — `src/hotel`

**외부 API**: [SerpApi Google Hotels](https://serpapi.com/google-hotels-api)  
**필요 키**: `SERPAPI_KEY`

#### 함수

```python
from src.hotel import search_google_hotels, print_hotel_results, HotelSearchRequest

result: HotelSearchResult = search_google_hotels(api_key: str, request: HotelSearchRequest)
print_hotel_results(result: HotelSearchResult, limit: int = 10)
```

#### 모델 (`src/hotel/models.py`)

```python
@dataclass
class HotelSearchRequest:
    q: str                          # 검색어 (예: "Seoul hotels")
    check_in_date: str              # 체크인 YYYY-MM-DD
    check_out_date: str             # 체크아웃 YYYY-MM-DD
    adults: int = 2
    children: int = 0
    children_ages: str | None = None   # 쉼표 구분 (예: "4,8")
    gl: str = "kr"                  # 국가 코드
    hl: str = "ko"                  # 언어 코드
    currency: str = "KRW"
    sort_by: int | None = None      # 3=가격순
    min_price: int | None = None
    max_price: int | None = None
    rating: int | None = None       # 최소 평점 1~10
    hotel_class: str | None = None  # 등급 (예: "3,4,5")
    free_cancellation: bool | None = None
    special_offers: bool | None = None
    eco_certified: bool | None = None
    vacation_rentals: bool | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    next_page_token: str | None = None
    no_cache: bool = False

@dataclass
class Hotel:
    name: str
    type: str | None
    hotel_class: str | None
    overall_rating: float | None
    reviews: int | None
    rate_per_night: str | None      # 1박 최저 요금
    total_rate: str | None          # 전체 요금
    amenities: list[str]
    property_token: str | None
    details_link: str | None

@dataclass
class HotelSearchResult:
    query: str
    check_in_date: str
    check_out_date: str
    adults: int
    total_results: int | None
    hotels: list[Hotel]
```

#### 사용 예시

```python
import os
from dotenv import load_dotenv
load_dotenv()

from src.hotel import search_google_hotels, HotelSearchRequest

request = HotelSearchRequest(
    q="Seoul hotels",
    check_in_date="2026-06-01",
    check_out_date="2026-06-03",
    adults=2,
    rating=8,
    hotel_class="4,5",
    free_cancellation=True,
)
result = search_google_hotels(os.getenv("SERPAPI_KEY"), request)

for hotel in result.hotels[:3]:
    print(f"{hotel.name} | 평점: {hotel.overall_rating} | 1박: {hotel.rate_per_night}")
```

---

### 3. 관광지/식당 — `src/tourist`

두 가지 검색 API를 제공합니다.

#### 3-1. Google Places

**외부 API**: [Google Places API (New)](https://developers.google.com/maps/documentation/places/web-service)  
**필요 키**: `GOOGLE_API_KEY`

```python
from src.tourist import search_places, Place

places: list[Place] = search_places(query: str)
```

#### 3-2. 네이버 지역 검색

**외부 API**: [네이버 검색 API](https://developers.naver.com/docs/serviceapi/search/local/local.md)  
**필요 키**: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`

```python
from src.tourist import search_local, LocalPlace

items: list[LocalPlace] = search_local(query: str, display: int = 5)
```

#### 모델 (`src/tourist/models.py`)

```python
@dataclass
class Place:
    name: str       # 장소명
    address: str    # 주소

@dataclass
class LocalPlace:
    title: str          # 장소명 (HTML 태그 제거됨)
    address: str        # 지번 주소
    road_address: str   # 도로명 주소
    telephone: str      # 전화번호
    category: str       # 업종 카테고리
    link: str           # 네이버 지도 링크
    map_x: str          # 경도 (카텍 좌표)
    map_y: str          # 위도 (카텍 좌표)
```

#### 사용 예시

```python
from src.tourist import search_places, search_local

# Google Places
for place in search_places("Tokyo Shibuya restaurants"):
    print(f"{place.name} — {place.address}")

# 네이버
for p in search_local("해운대 조용한 횟집"):
    print(f"{p.title} | {p.road_address} | {p.telephone}")
```

---

### 4. 교통 — `src/transport`

#### 4-1. 항공편

**외부 API**: [SerpApi Google Flights](https://serpapi.com/google-flights-api)  
**필요 키**: `SERPAPI_KEY`

```python
from src.transport import search_flights, FlightSearchResult

result: FlightSearchResult = search_flights(
    departure_id: str,          # 출발 공항 IATA (예: "ICN")
    arrival_id: str,            # 도착 공항 IATA (예: "NRT")
    outbound_date: str,         # 출발 날짜 YYYY-MM-DD
    return_date: str | None = None,  # 귀환 날짜 (왕복 시 입력)
    adults: int = 1,
    currency: str = "KRW",
    max_results: int = 3,
)
```

#### 4-2. 대중교통

**외부 API**: [SerpApi Google Maps Directions](https://serpapi.com/google-maps-directions-api)  
**필요 키**: `SERPAPI_KEY`

```python
from src.transport import search_transit, TransitSearchResult

result: TransitSearchResult = search_transit(
    start_addr: str,                    # 출발지 (예: "서울역")
    end_addr: str,                      # 도착지 (예: "부산역")
    depart_time: str | None = None,     # "YYYY-MM-DD HH:MM"
    prefer: str | None = None,          # "bus"|"subway"|"train"|"tram_light_rail"
    max_results: int = 3,
)
```

#### 모델 (`src/transport/models.py`)

```python
# 항공편 관련
@dataclass
class Layover:
    airport: str
    airport_code: str
    duration_minutes: int
    overnight: bool

@dataclass
class Flight:
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    stops: int
    price_per_person: int   # 원화
    total_price: int        # 원화 (1인 × adults)
    booking_url: str
    layovers: list[Layover]

@dataclass
class FlightSearchResult:
    departure: str          # 출발 IATA
    arrival: str            # 도착 IATA
    outbound_date: str
    adults: int
    currency: str
    return_date: str | None
    flights: list[Flight]
    error: str | None       # 항공편 없을 때만 존재

# 대중교통 관련
@dataclass
class Stop:
    name: str   # 정류장/역 이름
    time: str   # 시각

@dataclass
class TripSegment:
    mode: str               # "TRANSIT", "WALKING" 등
    title: str              # 노선명 (예: "KTX 101")
    start_stop: Stop
    end_stop: Stop
    stops_count: int
    service: str            # 운영사 (예: "코레일")
    duration_minutes: int

@dataclass
class Route:
    summary: str            # 경유 요약 (예: "KTX via 대전")
    duration_minutes: int
    formatted_duration: str # 예: "2시간 40분"
    distance: str           # 예: "325 km"
    start_time: str
    end_time: str
    cost: int | None
    currency: str
    trips: list[TripSegment]

@dataclass
class TransitSearchResult:
    start: str
    end: str
    routes: list[Route]
    error: str | None       # 경로 없을 때만 존재
```

#### 사용 예시

```python
from src.transport import search_flights, search_transit

# 항공편
result = search_flights("ICN", "NRT", "2026-06-01", adults=2)
if not result.error:
    for f in result.flights:
        print(f"{f.airline} {f.flight_number} | {f.departure_time}→{f.arrival_time} | {f.total_price:,}원")

# 대중교통
result = search_transit("서울역", "부산역", prefer="train")
if not result.error:
    for r in result.routes:
        print(f"{r.summary} | {r.formatted_duration} | {r.distance}")
        for seg in r.trips:
            if seg.mode != "WALKING":
                print(f"  [{seg.title}] {seg.start_stop.name} → {seg.end_stop.name}")
```

---

## 프로젝트 구조

```
src/
├── hotel/
│   ├── __init__.py         # search_google_hotels, print_hotel_results, 모델 export
│   ├── models.py           # HotelSearchRequest, Hotel, HotelSearchResult
│   └── search.py           # SerpApi Google Hotels 호출
├── tourist/
│   ├── __init__.py         # search_places, search_local, 모델 export
│   ├── models.py           # Place, LocalPlace
│   ├── google_places.py    # Google Places API 호출
│   └── naver_local.py      # 네이버 지역 검색 API 호출
├── transport/
│   ├── __init__.py         # search_flights, search_transit, 모델 export
│   ├── models.py           # Flight, FlightSearchResult, Route, TransitSearchResult 등
│   ├── flights.py          # SerpApi Google Flights 호출
│   └── transit.py          # SerpApi Google Maps Directions 호출
└── weather/
    ├── __init__.py         # get_weather, WeatherResult, DailyWeather export
    ├── models.py           # WeatherRequest, DailyWeather, WeatherResult
    ├── config.py           # API URL 및 상수
    ├── geocoding.py        # 도시명 → 좌표 (Nominatim)
    ├── forecast.py         # Open-Meteo API 호출
    └── display.py          # 콘솔 출력 포맷

main.py                     # 통합 CLI 진입점 (load_dotenv 여기서만 호출)
.env                        # API 키 모음
```
