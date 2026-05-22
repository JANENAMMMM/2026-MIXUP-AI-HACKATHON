# -*- coding: utf-8 -*-
"""API 엔드포인트, 요청 변수 목록, WMO 날씨 코드 상수 정의"""

# ── Geocoding ──────────────────────────────────────────────────────────────
# Nominatim(OpenStreetMap): 한글 포함 다국어 지원, API 키 불필요
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "WeatherApp/1.0 (mixup-hackathon)"}

# ── Open-Meteo 날씨 API (API 키 불필요) ────────────────────────────────────
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SEASONAL_URL = "https://seasonal-api.open-meteo.com/v1/seasonal"

# ── 일별 예보 변수 목록 ────────────────────────────────────────────────────
# archive API는 precipitation_probability_max 미지원 → get_archive에서 제외
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "precipitation_probability_max",
    "windspeed_10m_max",
    "windgusts_10m_max",
    "winddirection_10m_dominant",
    "uv_index_max",
    "shortwave_radiation_sum",
    "sunrise",
    "sunset",
    "daylight_duration",
    "sunshine_duration",
    "weathercode",
]

# ── 시즌 예보 변수 목록 (17일~9개월) ─────────────────────────────────────
# Seasonal API가 지원하는 변수만 포함
SEASONAL_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "windspeed_10m_max",
]

# ── WMO 날씨 코드 → 한글 설명 ─────────────────────────────────────────────
# 출처: https://open-meteo.com/en/docs
WMO_CODES = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "가벼운 이슬비",
    53: "보통 이슬비",
    55: "강한 이슬비",
    61: "가벼운 비",
    63: "보통 비",
    65: "강한 비",
    71: "가벼운 눈",
    73: "보통 눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "약한 소나기",
    81: "보통 소나기",
    82: "강한 소나기",
    85: "약한 눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우",
    96: "약한 우박 뇌우",
    99: "강한 우박 뇌우",
}
