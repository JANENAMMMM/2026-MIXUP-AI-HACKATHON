# -*- coding: utf-8 -*-
"""날씨 조회 패키지

사용법:
    from src.weather import get_weather
    result = get_weather('서울', 'today')
    result = get_weather('파리', '2026-07-21')
"""

from datetime import datetime
from .geocoding import get_coordinates
from .forecast import get_forecast, get_archive, get_seasonal
from .display import print_daily
from .models import DailyWeather, WeatherResult

_MAX_FORECAST_DAYS = 16
_MAX_SEASONAL_DAYS = 270


def get_weather(city: str, date_str: str) -> WeatherResult | None:
    """도시명과 날짜를 받아 날씨 정보를 출력하고 WeatherResult를 반환한다.

    날짜 범위에 따라 적절한 API를 자동으로 선택한다:
    - 과거        → ERA5 기상 재분석 데이터 (1940년~)
    - 오늘~+16일  → 단기 예보
    - +17~+270일  → 시즌 예보 (ECMWF SEAS5 앙상블 평균)

    Args:
        city:     도시명. 한글/영문 모두 가능 (예: '서울', 'Tokyo', 'New York')
        date_str: 날짜 문자열. 'today' 또는 'YYYY-MM-DD' 형식

    Returns:
        WeatherResult — 위치 정보와 DailyWeather를 담은 결과 객체.
        지원 범위를 초과하면 None 반환.
    """
    today = datetime.now().date()
    target = (
        today
        if date_str.lower() == "today"
        else datetime.strptime(date_str, "%Y-%m-%d").date()
    )
    delta = (target - today).days

    lat, lon, name, country, tz = get_coordinates(city)
    print(f"\n검색 위치: {name}, {country}")
    print(f"좌표:      위도 {lat:.4f}, 경도 {lon:.4f}")
    print(f"요청 날짜: {target}  (오늘 기준 {delta:+d}일)")

    if delta > _MAX_SEASONAL_DAYS:
        print(f"\n{_MAX_SEASONAL_DAYS}일(약 9개월) 초과는 지원되지 않습니다.")
        return None

    if delta < 0:
        raw = get_archive(lat, lon, target, target, tz)
        source = "과거 날씨 (ERA5 재분석)"
    elif delta <= _MAX_FORECAST_DAYS:
        raw = get_forecast(lat, lon, target, tz)
        source = f"예보 (D+{delta})"
    else:
        raw = get_seasonal(lat, lon, target, target, tz)
        source = f"시즌 예보 앙상블 평균 (D+{delta})"

    daily = DailyWeather.from_api_response(raw["daily"], target.isoformat())
    print_daily(daily, source)

    return WeatherResult(
        city=name,
        country=country,
        lat=lat,
        lon=lon,
        date=target.isoformat(),
        delta_days=delta,
        source=source,
        daily=daily,
    )


__all__ = ["get_weather", "WeatherResult", "DailyWeather"]
