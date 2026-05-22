# -*- coding: utf-8 -*-
"""날짜별 항공권 최저가 조회 패키지

사용법:
    from src.cheapest_date import get_cheapest_dates

    results = get_cheapest_dates(
        origin='ICN',
        destination='LHR',
        months=['202606', '202607', '202608', '202609'],
        trip_days=[4],          # 3박4일
        is_nonstop=False,
    )
    for r in results:
        print(r.date, r.return_date, r.price, r.stops)
"""

from .flight_crawler import get_cheapest_dates
from .models import FlightPrice

__all__ = ["get_cheapest_dates", "FlightPrice"]
