from dataclasses import dataclass, field


@dataclass
class FlightPrice:
    """날짜별 항공권 최저가 정보."""
    date: str                       # YYYY-MM-DD (출발일)
    return_date: str                # YYYY-MM-DD (귀국일)
    price: int                      # 원화
    stops: int = 0                  # 경유 횟수 (0 = 직항)
    duration: int = 0               # 비행시간 (분)
    airline_codes: list[str] = field(default_factory=list)
    trip_days: int = 0
    currency: str = "KRW"
