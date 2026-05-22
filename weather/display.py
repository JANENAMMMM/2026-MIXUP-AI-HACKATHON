# -*- coding: utf-8 -*-
"""날씨 데이터 콘솔 출력 포맷"""

from datetime import date
from .config import WMO_CODES


def _fmt(value, unit: str = "", fmt: str = ".1f") -> str:
    """값이 None이면 'N/A', 아니면 포맷 적용 후 단위를 붙인다."""
    return f"{value:{fmt}}{unit}" if value is not None else "N/A"


def print_daily(daily: dict, target_date: date, source_label: str) -> None:
    """일별 날씨 데이터를 콘솔에 출력한다.

    Args:
        daily: Open-Meteo daily 응답 dict (key: 변수명, value: 날짜별 리스트)
        target_date: 출력할 날짜
        source_label: 헤더에 표시할 데이터 출처 (예: '예보 (D+3)')
    """
    dates = daily.get("time", [])
    date_str = target_date.isoformat()

    if date_str not in dates:
        print(f"  {date_str} 데이터 없음")
        return

    i = dates.index(date_str)

    def get(key):
        return daily.get(key, [None] * len(dates))[i]

    print(f"\n{'=' * 55}")
    print(f" {target_date.strftime('%Y년 %m월 %d일')}  [{source_label}]")
    print(f"{'=' * 55}")

    # 날씨 상태
    wcode = get("weathercode")
    if wcode is not None:
        desc = WMO_CODES.get(int(wcode), f"코드 {wcode}")
        print(f"\n[날씨 상태]  {desc} (WMO {wcode})")

    # 기온
    print(
        f"\n[기온]       최고: {_fmt(get('temperature_2m_max'), '°C')}"
        f"  최저: {_fmt(get('temperature_2m_min'), '°C')}"
        f"  평균: {_fmt(get('temperature_2m_mean'), '°C')}"
    )
    print(
        f"[체감기온]   최고: {_fmt(get('apparent_temperature_max'), '°C')}"
        f"  최저: {_fmt(get('apparent_temperature_min'), '°C')}"
    )

    # 강수
    print(
        f"\n[강수 합계]  {_fmt(get('precipitation_sum'), ' mm')}"
        f"  (비: {_fmt(get('rain_sum'), ' mm')}"
        f"  눈: {_fmt(get('snowfall_sum'), ' cm')})"
    )
    print(
        f"[강수 시간]  {_fmt(get('precipitation_hours'), ' h', '.0f')}"
        f"  강수 확률(최대): {_fmt(get('precipitation_probability_max'), '%', '.0f')}"
    )

    # 바람
    print(
        f"\n[바람]       최대: {_fmt(get('windspeed_10m_max'), ' km/h')}"
        f"  돌풍: {_fmt(get('windgusts_10m_max'), ' km/h')}"
        f"  방향: {_fmt(get('winddirection_10m_dominant'), '°', '.0f')}"
    )

    # 일조/일사
    sun = get("sunshine_duration")
    dlen = get("daylight_duration")
    print(f"\n[UV 지수]    최대: {_fmt(get('uv_index_max'))}")
    print(f"[일사량]     {_fmt(get('shortwave_radiation_sum'), ' MJ/m²')}")
    print(
        f"[일조시간]   {f'{sun / 3600:.1f} h' if sun is not None else 'N/A'}"
        f"  (낮길이: {f'{dlen / 3600:.1f} h' if dlen is not None else 'N/A'})"
    )

    # 일출/일몰 (ISO 문자열에서 시간 부분만 추출)
    sunrise = get("sunrise")
    sunset = get("sunset")
    if sunrise and sunset:
        print(f"\n[일출]       {sunrise[11:16]}  [일몰] {sunset[11:16]}")

    print()
