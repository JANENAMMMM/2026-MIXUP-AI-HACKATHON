from dataclasses import dataclass


@dataclass
class Place:
    """Google Places 검색 결과 장소."""
    name: str
    address: str
    lat: float = 0.0
    lng: float = 0.0

    @classmethod
    def from_api_response(cls, data: dict) -> "Place":
        loc = data.get("location", {})
        return cls(
            name=data.get("displayName", {}).get("text", ""),
            address=data.get("formattedAddress", ""),
            lat=float(loc.get("latitude", 0.0)),
            lng=float(loc.get("longitude", 0.0)),
        )


@dataclass
class LocalPlace:
    """네이버 지역 검색 결과 장소."""
    title: str
    address: str
    road_address: str = ""
    telephone: str = ""
    category: str = ""
    link: str = ""
    map_x: str = ""
    map_y: str = ""
    lat: float = 0.0
    lng: float = 0.0

    @classmethod
    def from_api_response(cls, data: dict) -> "LocalPlace":
        raw_x = data.get("mapx", "")
        raw_y = data.get("mapy", "")
        # Naver mapx/mapy는 WGS84 경위도 × 10^7
        lat = int(raw_y) / 1e7 if raw_y else 0.0
        lng = int(raw_x) / 1e7 if raw_x else 0.0
        return cls(
            title=data.get("title", "").replace("<b>", "").replace("</b>", ""),
            address=data.get("address", ""),
            road_address=data.get("roadAddress", ""),
            telephone=data.get("telephone", ""),
            category=data.get("category", ""),
            link=data.get("link", ""),
            map_x=raw_x,
            map_y=raw_y,
            lat=lat,
            lng=lng,
        )
