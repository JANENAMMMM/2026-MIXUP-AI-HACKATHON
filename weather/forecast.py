# -*- coding: utf-8 -*-
"""Open-Meteo API를 통한 날씨 데이터 조회

날짜 범위에 따라 세 가지 API를 사용한다:
- 과거      : Historical Archive API (1940년~)
- 0~16일    : Forecast API
- 17~270일  : Seasonal Forecast API (ECMWF SEAS5 앙상블 평균)
"""

from datetime import date, datetime
import requests
from .config import (
    ARCHIVE_URL,
    DAILY_VARS,
    FORECAST_URL,
    SEASONAL_URL,
    SEASONAL_VARS,
)


def get_forecast(lat: float, lon: float, end_date: date, timezone: str) -> dict:
    """오늘부터 end_date까지의 일별 예보를 가져온다 (최대 16일).

    Args:
        lat: 위도
        lon: 경도
        end_date: 조회 마지막 날짜
        timezone: 타임존 문자열 ('auto' 사용 시 좌표 기반 자동 결정)

    Returns:
        Open-Meteo API 응답 JSON
    """
    today = datetime.now().date()
    forecast_days = max(1, min((end_date - today).days + 1, 16))

    resp = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(DAILY_VARS),
            "timezone": timezone,
            "forecast_days": forecast_days,
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_archive(
    lat: float, lon: float, start_date: date, end_date: date, timezone: str
) -> dict:
    """과거 날씨 데이터를 ERA5 재분석 데이터에서 가져온다 (1940년~).

    Args:
        lat: 위도
        lon: 경도
        start_date: 조회 시작 날짜
        end_date: 조회 마지막 날짜
        timezone: 타임존 문자열

    Returns:
        Open-Meteo Archive API 응답 JSON
    """
    # Archive API는 precipitation_probability_max 미지원
    archive_vars = [v for v in DAILY_VARS if v != "precipitation_probability_max"]

    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(archive_vars),
            "timezone": timezone,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_seasonal(
    lat: float, lon: float, start_date: date, end_date: date, timezone: str
) -> dict:
    """시즌 예보를 가져와 앙상블 평균으로 변환한다 (최대 9개월).

    ECMWF SEAS5 모델의 앙상블 멤버(최대 51개)를 평균내어 반환한다.

    Args:
        lat: 위도
        lon: 경도
        start_date: 조회 시작 날짜
        end_date: 조회 마지막 날짜
        timezone: 타임존 문자열

    Returns:
        앙상블 평균값이 담긴 dict (Open-Meteo 응답과 동일한 구조)
    """
    # 기본 변수명만 요청 → API가 member01~51 자동 반환
    resp = requests.get(
        SEASONAL_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(SEASONAL_VARS),
            "timezone": timezone,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )
    resp.raise_for_status()
    raw = resp.json()

    # 앙상블 멤버 평균 계산
    daily_raw = raw.get("daily", {})
    dates = daily_raw.get("time", [])
    averaged: dict = {"time": dates}

    for var in SEASONAL_VARS:
        members = [v for k, v in daily_raw.items() if k.startswith(var + "_member")]
        if not members:
            continue
        averaged[var] = [
            round(
                sum(m[i] for m in members if m[i] is not None)
                / sum(1 for m in members if m[i] is not None),
                1,
            )
            if any(m[i] is not None for m in members)
            else None
            for i in range(len(dates))
        ]

    raw["daily"] = averaged
    return raw
