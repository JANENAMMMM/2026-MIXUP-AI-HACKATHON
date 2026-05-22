from dataclasses import dataclass


@dataclass
class WeatherRequest:
    """날씨 조회 요청."""
    city: str       # 도시명 (한글/영문, 예: '서울', 'Tokyo')
    date: str       # 'today' 또는 'YYYY-MM-DD'


@dataclass
class DailyWeather:
    """하루 날씨 데이터."""
    date: str
    weather_code: int | None = None
    temp_max: float | None = None           # 최고 기온 (°C)
    temp_min: float | None = None           # 최저 기온 (°C)
    temp_mean: float | None = None          # 평균 기온 (°C)
    apparent_temp_max: float | None = None  # 최고 체감 기온 (°C)
    apparent_temp_min: float | None = None  # 최저 체감 기온 (°C)
    precipitation_sum: float | None = None  # 총 강수량 (mm)
    rain_sum: float | None = None           # 강우량 (mm)
    snowfall_sum: float | None = None       # 적설량 (cm)
    precipitation_hours: float | None = None
    precipitation_probability_max: float | None = None  # 최대 강수 확률 (%)
    windspeed_max: float | None = None      # 최대 풍속 (km/h)
    windgusts_max: float | None = None      # 최대 돌풍 (km/h)
    wind_direction: float | None = None     # 풍향 (°)
    uv_index_max: float | None = None
    shortwave_radiation_sum: float | None = None  # 일사량 (MJ/m²)
    sunshine_duration: float | None = None  # 일조 시간 (초)
    daylight_duration: float | None = None  # 낮 길이 (초)
    sunrise: str | None = None              # ISO 시각 문자열
    sunset: str | None = None

    @classmethod
    def from_api_response(cls, daily: dict, target_date: str) -> "DailyWeather":
        dates = daily.get("time", [])
        if target_date not in dates:
            return cls(date=target_date)
        i = dates.index(target_date)

        def get(key):
            vals = daily.get(key, [])
            return vals[i] if i < len(vals) else None

        return cls(
            date=target_date,
            weather_code=get("weathercode"),
            temp_max=get("temperature_2m_max"),
            temp_min=get("temperature_2m_min"),
            temp_mean=get("temperature_2m_mean"),
            apparent_temp_max=get("apparent_temperature_max"),
            apparent_temp_min=get("apparent_temperature_min"),
            precipitation_sum=get("precipitation_sum"),
            rain_sum=get("rain_sum"),
            snowfall_sum=get("snowfall_sum"),
            precipitation_hours=get("precipitation_hours"),
            precipitation_probability_max=get("precipitation_probability_max"),
            windspeed_max=get("windspeed_10m_max"),
            windgusts_max=get("windgusts_10m_max"),
            wind_direction=get("winddirection_10m_dominant"),
            uv_index_max=get("uv_index_max"),
            shortwave_radiation_sum=get("shortwave_radiation_sum"),
            sunshine_duration=get("sunshine_duration"),
            daylight_duration=get("daylight_duration"),
            sunrise=get("sunrise"),
            sunset=get("sunset"),
        )


@dataclass
class WeatherResult:
    """날씨 조회 전체 결과 (위치 정보 + 일별 날씨)."""
    city: str
    country: str
    lat: float
    lon: float
    date: str
    delta_days: int     # 오늘 기준 +/- 일수
    source: str         # '과거 날씨 (ERA5)', '예보', '시즌 예보'
    daily: DailyWeather | None = None
