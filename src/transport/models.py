from dataclasses import dataclass, field


@dataclass
class Layover:
    """항공편 경유지 정보."""
    airport: str
    airport_code: str
    duration_minutes: int
    overnight: bool = False

    @classmethod
    def from_api_response(cls, data: dict) -> "Layover":
        return cls(
            airport=data.get("name", ""),
            airport_code=data.get("id", ""),
            duration_minutes=data.get("duration", 0),
            overnight=data.get("overnight", False),
        )


@dataclass
class Flight:
    """개별 항공편 정보."""
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    stops: int
    price_per_person: int
    total_price: int
    booking_url: str
    layovers: list[Layover] = field(default_factory=list)


@dataclass
class FlightSearchResult:
    """항공편 검색 결과."""
    departure: str          # 출발 공항 IATA 코드
    arrival: str            # 도착 공항 IATA 코드
    outbound_date: str
    adults: int
    currency: str
    return_date: str | None = None
    flights: list[Flight] = field(default_factory=list)
    error: str | None = None


@dataclass
class Stop:
    """대중교통 정류장/역 정보."""
    name: str
    time: str

    @classmethod
    def from_api_response(cls, data: dict) -> "Stop":
        return cls(name=data.get("name", ""), time=data.get("time", ""))


@dataclass
class TripSegment:
    """대중교통 구간 정보 (한 노선/수단)."""
    mode: str               # TRANSIT, WALKING 등
    title: str              # 노선명 (예: "KTX 101")
    start_stop: Stop
    end_stop: Stop
    stops_count: int
    service: str            # 운영사 (예: "코레일")
    duration_minutes: int

    @classmethod
    def from_api_response(cls, data: dict) -> "TripSegment":
        return cls(
            mode=data.get("travel_mode", ""),
            title=data.get("title", ""),
            start_stop=Stop.from_api_response(data.get("start_stop", {})),
            end_stop=Stop.from_api_response(data.get("end_stop", {})),
            stops_count=len(data.get("stops", [])),
            service=data.get("service_run_by", {}).get("name", ""),
            duration_minutes=data.get("duration", 0) // 60,
        )


@dataclass
class Route:
    """대중교통 경로 (출발지→도착지 전체 경로)."""
    summary: str
    duration_minutes: int
    formatted_duration: str
    distance: str
    start_time: str
    end_time: str
    cost: int | None
    currency: str
    trips: list[TripSegment] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "Route":
        trips = [TripSegment.from_api_response(t) for t in data.get("trips", [])]
        transit_trips = [t for t in trips if t.mode.lower() == "transit"]
        summary = data.get("via") or (transit_trips[0].title if transit_trips else "")
        return cls(
            summary=summary,
            duration_minutes=data.get("duration", 0) // 60,
            formatted_duration=data.get("formatted_duration", ""),
            distance=data.get("formatted_distance", ""),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            cost=data.get("cost"),
            currency=data.get("currency", ""),
            trips=trips,
        )


@dataclass
class TransitSearchResult:
    """대중교통 경로 검색 결과."""
    start: str
    end: str
    routes: list[Route] = field(default_factory=list)
    error: str | None = None
