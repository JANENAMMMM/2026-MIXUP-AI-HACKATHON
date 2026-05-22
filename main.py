# -*- coding: utf-8 -*-
"""날씨 조회 실행 진입점

사용법:
    python main.py                        # 기본 예시 실행
    python main.py Seoul today            # 인자로 직접 입력
    python main.py "New York" 2026-07-01
"""

import sys
from datetime import datetime, timedelta
from weather import get_weather


def main():
    # 커맨드라인 인자가 있으면 인자 우선
    if len(sys.argv) == 3:
        city = sys.argv[1]
        date_str = sys.argv[2]
        get_weather(city, date_str)
        return

    # 기본 예시: 여러 도시 × 날짜 범위
    today = datetime.now().date()

    examples = [
        ("서울",  (today - timedelta(days=30)).isoformat()),  # 과거
        ("도쿄",  "today"),                                    # 오늘
        ("뉴욕",  (today + timedelta(days=10)).isoformat()),   # 단기 예보
        ("파리",  (today + timedelta(days=60)).isoformat()),   # 시즌 예보
        ("홍콩",  (today + timedelta(days=90)).isoformat()),   # 시즌 예보
    ]

    for city, date_str in examples:
        get_weather(city, date_str)


if __name__ == "__main__":
    main()
