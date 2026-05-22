from dataclasses import dataclass


@dataclass
class Place:
    """Google Places 검색 결과 장소."""
    name: str
    address: str

    @classmethod
    def from_api_response(cls, data: dict) -> "Place":
        return cls(
            name=data.get("displayName", {}).get("text", ""),
            address=data.get("formattedAddress", ""),
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

    @classmethod
    def from_api_response(cls, data: dict) -> "LocalPlace":
        return cls(
            title=data.get("title", "").replace("<b>", "").replace("</b>", ""),
            address=data.get("address", ""),
            road_address=data.get("roadAddress", ""),
            telephone=data.get("telephone", ""),
            category=data.get("category", ""),
            link=data.get("link", ""),
            map_x=data.get("mapx", ""),
            map_y=data.get("mapy", ""),
        )
