from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from weather.forecast import get_forecast
from weather.geocoding import get_coordinates

# ==========================================
# 1. Geocoding (위경도 변환) Tool
# ==========================================
class GeocodingArgs(BaseModel):
    location: str = Field(..., description="위도와 경도를 찾을 도시, 지역 또는 명소의 이름 (예: '도쿄', '해운대', 'New York')")

@tool(args_schema=GeocodingArgs)
def tool_get_coordinates(location: str) -> Dict[str, Any]:
    """
    입력한 도시, 지역 또는 명소 이름의 정확한 위도(lat)와 경도(lon) 좌표 및 타임존을 검색하는 도구입니다.
    """
    try:
        lat, lon, name, country, tz = get_coordinates(location)
        
        return {
            "location_query": location,
            "resolved_name": name,
            "country": country,
            "lat": lat,
            "lon": lon,
            "timezone": tz
        }
    except Exception as e:
        return {"error": f"좌표 검색 실패: {str(e)}"}

# ==========================================
# 2. Weather (날씨 예보) Tool
# ==========================================
class WeatherArgs(BaseModel):
    lat: float = Field(..., description="위도 좌표 (tool_get_coordinates에서 얻은 값 사용)")
    lon: float = Field(..., description="경도 좌표 (tool_get_coordinates에서 얻은 값 사용)")
    end_date: str = Field(..., description="조회할 날짜 (YYYY-MM-DD 형식)")
    timezone: str = Field(default="auto", description="타임존 (기본: 'auto' 또는 tool_get_coordinates에서 얻은 값)")

@tool(args_schema=WeatherArgs)
def tool_get_weather(lat: float, lon: float, end_date: str, timezone: str = "auto") -> Dict[str, Any]:
    """
    특정 위도(lat)와 경도(lon) 좌표를 기준으로 해당 날짜의 날씨 상태 및 최고/최저 기온을 조회하는 도구입니다.
    """
    try:
        target_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        result = get_forecast(lat=lat, lon=lon, end_date=target_date, timezone=timezone)
        daily = result.get("daily", {})
        return {
            "date": end_date,
            "weather_code": daily.get("weathercode", [])[-1] if daily.get("weathercode") else "알 수 없음",
            "max_temp": daily.get("temperature_2m_max", [])[-1] if daily.get("temperature_2m_max") else None,
            "min_temp": daily.get("temperature_2m_min", [])[-1] if daily.get("temperature_2m_min") else None,
        }
    except Exception as e:
        return {"error": f"날씨 정보 조회 실패: {str(e)}"}