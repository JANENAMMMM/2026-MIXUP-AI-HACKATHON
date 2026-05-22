# -*- coding: utf-8 -*-
"""Open-Meteo API를 통한 날씨 데이터 조회"""

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
