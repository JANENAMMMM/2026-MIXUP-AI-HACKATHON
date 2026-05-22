from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# weather 폴더에 있는 원본 함수들을 가져옵니다.
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
    특정 지역의 위도(lat)와 경도(lon) 좌표를 검색합니다. 
    날씨 예보를 조회(tool_get_weather)하기 전에, LLM은 반드시 먼저 이 도구를 사용하여 타겟 지역의 위경도 좌표를 얻어야 합니다.
    """
    try:
        # get_coordinates는 (lat, lon, name, country, timezone) 튜플을 반환합니다.
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
    특정 위도/경도 좌표의 날씨 예보(날씨 상태, 최고/최저 기온)를 확인합니다.
    """
    try:
        # LLM이 전달한 날짜 문자열을 datetime.date 객체로 변환
        target_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # 원본 날씨 조회 API 호출
        result = get_forecast(lat=lat, lon=lon, end_date=target_date, timezone=timezone)
        
        daily = result.get("daily", {})
        
        # LLM이 읽기 편하도록 요청한 날짜(배열의 마지막 요소)의 핵심 데이터만 요약하여 반환
        return {
            "date": end_date,
            "weather_code": daily.get("weathercode", [])[-1] if daily.get("weathercode") else "알 수 없음",
            "max_temp": daily.get("temperature_2m_max", [])[-1] if daily.get("temperature_2m_max") else None,
            "min_temp": daily.get("temperature_2m_min", [])[-1] if daily.get("temperature_2m_min") else None,
        }
    except Exception as e:
        return {"error": f"날씨 정보 조회 실패: {str(e)}"}