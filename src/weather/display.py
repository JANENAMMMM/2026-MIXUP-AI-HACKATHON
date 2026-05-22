# -*- coding: utf-8 -*-
"""날씨 데이터 콘솔 출력 포맷"""

from .config import WMO_CODES
from .models import DailyWeather


def _fmt(value, unit: str = "", fmt: str = ".1f") -> str:
    return f"{value:{fmt}}{unit}" if value is not None else "N/A"


def print_daily(weather: DailyWeather, source_label: str) -> None:
    """DailyWeather를 콘솔에 출력한다.

    Args:
        weather:      출력할 하루 날씨 데이터
        source_label: 헤더에 표시할 데이터 출처 (예: '예보 (D+3)')
    """
    from datetime import date as date_type
    import datetime

    try:
        target_date = datetime.date.fromisoformat(weather.date)
    except ValueError:
        print(f"  {weather.date} 날짜 형식 오류")
        return

    if weather.temp_max is None and weather.weather_code is None:
        print(f"  {weather.date} 데이터 없음")
        return

    print(f"\n{'=' * 55}")
    print(f" {target_date.strftime('%Y년 %m월 %d일')}  [{source_label}]")
    print(f"{'=' * 55}")

    if weather.weather_code is not None:
        desc = WMO_CODES.get(int(weather.weather_code), f"코드 {weather.weather_code}")
        print(f"\n[날씨 상태]  {desc} (WMO {weather.weather_code})")

    print(
        f"\n[기온]       최고: {_fmt(weather.temp_max, '°C')}"
        f"  최저: {_fmt(weather.temp_min, '°C')}"
        f"  평균: {_fmt(weather.temp_mean, '°C')}"
    )
    print(
        f"[체감기온]   최고: {_fmt(weather.apparent_temp_max, '°C')}"
        f"  최저: {_fmt(weather.apparent_temp_min, '°C')}"
    )

    print(
        f"\n[강수 합계]  {_fmt(weather.precipitation_sum, ' mm')}"
        f"  (비: {_fmt(weather.rain_sum, ' mm')}"
        f"  눈: {_fmt(weather.snowfall_sum, ' cm')})"
    )
    print(
        f"[강수 시간]  {_fmt(weather.precipitation_hours, ' h', '.0f')}"
        f"  강수 확률(최대): {_fmt(weather.precipitation_probability_max, '%', '.0f')}"
    )

    print(
        f"\n[바람]       최대: {_fmt(weather.windspeed_max, ' km/h')}"
        f"  돌풍: {_fmt(weather.windgusts_max, ' km/h')}"
        f"  방향: {_fmt(weather.wind_direction, '°', '.0f')}"
    )

    sun = weather.sunshine_duration
    dlen = weather.daylight_duration
    print(f"\n[UV 지수]    최대: {_fmt(weather.uv_index_max)}")
    print(f"[일사량]     {_fmt(weather.shortwave_radiation_sum, ' MJ/m²')}")
    print(
        f"[일조시간]   {f'{sun / 3600:.1f} h' if sun is not None else 'N/A'}"
        f"  (낮길이: {f'{dlen / 3600:.1f} h' if dlen is not None else 'N/A'})"
    )

    if weather.sunrise and weather.sunset:
        print(f"\n[일출]       {weather.sunrise[11:16]}  [일몰] {weather.sunset[11:16]}")

    print()
