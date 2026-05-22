# -*- coding: utf-8 -*-
"""날씨 데이터 콘솔 출력 — 이용 가능한 필드만 한 줄로 출력."""

from .config import WMO_CODES
from .models import DailyWeather


def print_daily(weather: DailyWeather, source_label: str) -> None:
    """DailyWeather에서 None이 아닌 핵심 필드만 추려 한 줄로 출력한다.

    시즌 예보처럼 일부 필드가 없는 경우에도 깔끔하게 출력된다.
    """
    if weather.temp_max is None and weather.weather_code is None:
        print(f"  {weather.date} 데이터 없음")
        return

    import datetime
    try:
        d = datetime.date.fromisoformat(weather.date)
        date_str = d.strftime("%Y-%m-%d")
    except ValueError:
        date_str = weather.date

    parts = [f"[{date_str}]"]

    if weather.temp_max is not None:
        temp = f"최고 {weather.temp_max:.1f}°C"
        if weather.temp_min is not None:
            temp += f" / 최저 {weather.temp_min:.1f}°C"
        parts.append(temp)

    if weather.precipitation_probability_max is not None:
        parts.append(f"강수확률 {weather.precipitation_probability_max:.0f}%")

    if weather.precipitation_sum is not None:
        parts.append(f"강수 {weather.precipitation_sum:.1f}mm")

    if weather.weather_code is not None:
        desc = WMO_CODES.get(int(weather.weather_code), f"WMO {weather.weather_code}")
        parts.append(desc)

    parts.append(f"[{source_label}]")
    print("  " + " | ".join(parts))
