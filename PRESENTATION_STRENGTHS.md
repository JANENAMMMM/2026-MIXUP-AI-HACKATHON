# 발표용 강점 정리

이 프로젝트의 핵심은 단순한 여행 추천기가 아니라, 사용자의 한 문장을 실제 여행 실행 계획으로 바꾸는 AI 에이전트 시스템이라는 점입니다. 코드 전체를 보면 "질문을 이해하는 단계"와 "외부 데이터를 모으는 단계", "조건을 계산하는 단계", "최종 일정을 합성하는 단계"가 명확히 분리되어 있습니다. 그래서 발표에서는 "LLM을 붙인 서비스"가 아니라 "업무를 분해하고, 각 분해된 작업을 tool로 수행하는 에이전트 아키텍처"라고 말하는 것이 가장 강력합니다.

## 1. 한 줄로 설명되는 강점

이 프로젝트는 자연어 여행 요청을 받아 목적지, 날짜, 예산, 인원, 숙소, 날씨, 장소, 동선까지 단계적으로 수집하고, 그 결과를 하나의 완성된 여행 일정으로 합성하는 end-to-end AI travel agent입니다.

발표용으로는 이렇게 말할 수 있습니다.

"이 서비스의 강점은 LLM이 답변을 잘하는 데 있지 않습니다. 사용자의 의도를 구조화하고, 여러 외부 API를 조합하고, 그 결과를 다시 일정이라는 형태로 재조립하는 실행형 에이전트라는 데 있습니다."

## 2. 코드로 증명되는 판단 기준

아래 항목들은 발표에서 특히 설득력이 큽니다. 왜냐하면 단순한 설명이 아니라, 실제 코드에 있는 계산식과 조건문으로 바로 증명할 수 있기 때문입니다.

| 주장                           | 코드 근거                                                              | 실제 계산/판단 방식                                                                                                                                            |
| ------------------------------ | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 날짜 미정도 추천 가능          | [src/agent/nodes/date_optimizer.py](src/agent/nodes/date_optimizer.py) | 월만 들어오면 후보 날짜를 만들고, 항공권과 날씨를 함께 점수화한 뒤 `score` 내림차순으로 정렬합니다.                                                            |
| 날씨를 정량 점수로 평가        | [src/agent/nodes/date_optimizer.py](src/agent/nodes/date_optimizer.py) | 날씨 코드 `<= 2`면 `+3`, `== 3`이면 `+2`, `< 60`이면 `+1`, 최고기온이 `18~28°C`면 `+1`, 강수확률이 `20% 미만`이면 `+1`을 더하고, 마지막에 일수로 나눕니다.     |
| 항공권 가격을 수치화           | [src/agent/nodes/date_optimizer.py](src/agent/nodes/date_optimizer.py) | `price_score = 2.5` 또는 `(max_price - flight.price) / price_range * 5`로 정규화하고, 직항 선호 시 경유 패널티를 더 크게 줍니다.                               |
| 숙소 예산을 먼저 자름          | [src/agent/nodes/stay_node.py](src/agent/nodes/stay_node.py)           | 항공권이 없으면 총예산의 `60%`를 숙박 상한으로 쓰고, 항공권이 있으면 남은 예산의 `90%`를 숙박 상한으로 사용합니다. 이후 `nights`로 나눠 1박 상한을 계산합니다. |
| 장소 수를 숙박일수에 맞춤      | [src/agent/nodes/place_node.py](src/agent/nodes/place_node.py)         | 맛집은 `min(nights + 1, 6)`, 명소는 `min(nights * 2 + 1, 10)`으로 목표 개수를 정해 여행 일수에 맞는 밀도를 유지합니다.                                         |
| 동선을 거리 기반으로 최적화    | [src/agent/nodes/place_node.py](src/agent/nodes/place_node.py)         | 좌표가 있는 후보만 모아 Haversine 거리로 계산하고, 최근접 이웃 그리디로 방문 순서를 정합니다.                                                                  |
| 국내/해외에 따라 다른 API 사용 | [src/agent/nodes/place_node.py](src/agent/nodes/place_node.py)         | `IATA` 기준으로 국내면 Naver Local, 해외면 Google Places로 분기합니다.                                                                                         |
| 중간 선택이 있어도 상태 유지   | [src/agent/graph.py](src/agent/graph.py)                               | `MemorySaver` 체크포인트와 `interrupt/resume` 구조를 써서 날짜 선택, 호텔 조건 선택, 호텔 선택을 중간에 끊었다가 다시 이어갑니다.                              |

발표에서 바로 쓰기 좋은 한 문장도 같이 적어두면 좋습니다.

"이 프로젝트는 느낌으로 추천하지 않습니다. 날짜는 점수화하고, 숙소는 예산 비율로 자르고, 장소는 여행 일수에 맞춰 개수를 정하고, 동선은 실제 좌표 거리로 정렬합니다."

## 3. 외부 API와 Tool 구성

이 프로젝트의 핵심 설득 포인트는 `src`가 실제로 쏘는 외부 서비스가 분명하다는 점입니다. 즉, 백엔드 자체의 REST API가 아니라, 여행 계획을 만들기 위해 어떤 외부 API를 어디서 호출하는지를 숫자로 보여줄 수 있습니다.

외부 API를 호출하는 소스 파일은 9개입니다.

- [src/weather/forecast.py](src/weather/forecast.py)
- [src/weather/geocoding.py](src/weather/geocoding.py)
- [src/hotel/search.py](src/hotel/search.py)
- [src/tourist/google_places.py](src/tourist/google_places.py)
- [src/tourist/naver_local.py](src/tourist/naver_local.py)
- [src/transport/flights.py](src/transport/flights.py)
- [src/transport/transit.py](src/transport/transit.py)
- [src/cheapest_date/flight_crawler.py](src/cheapest_date/flight_crawler.py)
- [src/agent/llm.py](src/agent/llm.py)

실제 호출 대상 엔드포인트는 대표적으로 11개입니다.

- `https://api.open-meteo.com/v1/forecast`
- `https://archive-api.open-meteo.com/v1/archive`
- `https://seasonal-api.open-meteo.com/v1/seasonal`
- `https://nominatim.openstreetmap.org/search`
- `https://serpapi.com/search.json` (호텔 검색)
- `https://serpapi.com/search` (항공편 검색)
- `https://serpapi.com/search` (대중교통 경로 검색)
- `https://places.googleapis.com/v1/places:searchText`
- `https://openapi.naver.com/v1/search/local.json`
- `https://flight-api.naver.com/graphql`
- `ChatUpstage`로 연결되는 Upstage LLM

대표적으로 어디서 쏘는지도 같이 말할 수 있습니다.

- `src/weather/forecast.py`: Open-Meteo Forecast / Archive / Seasonal
- `src/weather/geocoding.py`: Nominatim 지오코딩
- `src/hotel/search.py`: SerpApi Google Hotels
- `src/tourist/google_places.py`: Google Places API (GCP)
- `src/tourist/naver_local.py`: 네이버 지역 검색 API
- `src/transport/flights.py`: SerpApi Google Flights
- `src/transport/transit.py`: SerpApi Google Maps Directions
- `src/cheapest_date/flight_crawler.py`: 네이버 항공권 GraphQL 우선, SerpApi fallback
- `src/agent/llm.py`: Upstage Solar 계열 LLM

대표 파라미터는 다음과 같습니다.

- 날씨: `latitude`, `longitude`, `daily`, `timezone`, `forecast_days`, `start_date`, `end_date`
- 지오코딩: `q`, `format`, `limit`, `addressdetails`
- 호텔: `engine`, `q`, `check_in_date`, `check_out_date`, `adults`, `max_price`, `sort_by`, `rating`, `hotel_class`
- Google Places: `textQuery`, `X-Goog-Api-Key`, `X-Goog-FieldMask`
- Naver Local: `query`, `display`, `X-Naver-Client-Id`, `X-Naver-Client-Secret`
- 항공권: `departure_id`, `arrival_id`, `outbound_date`, `return_date`, `engine`, `currency`, `hl`, `gl`
- 대중교통: `start_addr`, `end_addr`, `travel_mode`, `prefer`, `depart_time`
- 네이버 항공권: `departureLocationCode`, `arrivalLocationCode`, `departureMonths`, `isNonstop`, `tripDays`, `tripType`
- Upstage LLM: `model`, `temperature`, `UPSTAGE_API_KEY`

Tool은 총 8개입니다.

- [src/tools/hotel_tool.py](src/tools/hotel_tool.py)
  - `tool_search_hotels(query, check_in_date, check_out_date, adults, max_price)`
- [src/tools/weather_tool.py](src/tools/weather_tool.py)
  - `tool_get_coordinates(location)`
  - `tool_get_weather(lat, lon, end_date, timezone)`
- [src/tools/tourist_tool.py](src/tools/tourist_tool.py)
  - `tool_search_intl_places(query)`
  - `tool_search_domestic_places(query)`
- [src/tools/transport_tools.py](src/tools/transport_tools.py)
  - `tool_search_flights(departure_id, arrival_id, outbound_date, return_date)`
  - `tool_search_transit(start_addr, end_addr)`
- [src/tools/cheapest_date_tool.py](src/tools/cheapest_date_tool.py)
  - `tool_get_cheapest_flight_dates(origin, destination, months, trip_days, is_nonstop)`

발표에서는 이렇게 정리할 수 있습니다.

"이 프로젝트는 외부 API 소스 파일 9개와 대표 엔드포인트 11개를 연결하고, 그 위에 tool 8개를 얹어서 에이전트가 필요한 데이터만 골라 쓰도록 설계했습니다. 날씨, 지도, 장소, 항공, 호텔, LLM이 모두 분리되어 있어서 책임이 명확합니다."

### Python 슈도코드

```python
class TravelAgent:
	def __init__(self):
		self.tools = {
			"hotel": tool_search_hotels,
			"weather": tool_get_weather,
			"coordinates": tool_get_coordinates,
			"intl_places": tool_search_intl_places,
			"domestic_places": tool_search_domestic_places,
			"flights": tool_search_flights,
			"transit": tool_search_transit,
			"cheapest_dates": tool_get_cheapest_flight_dates,
		}

	def plan(self, message, budget=None, people=None, stay=None):
		intent = self.extract_intent(message, budget, people, stay)

		if intent.date_is_fixed:
			dates = (intent.check_in, intent.check_out)
		else:
			date_candidates = self.tools["cheapest_dates"](
				origin=intent.origin,
				destination=intent.destination,
				months=intent.target_months,
				trip_days=[intent.trip_nights + 1],
				is_nonstop=intent.prefer_nonstop,
			)
			dates = date_candidates[0]

		weather = self.tools["weather"](...)
		hotel_candidates = self.tools["hotel"](...)
		if intent.is_domestic:
			place_candidates = self.tools["domestic_places"](...)
		else:
			place_candidates = self.tools["intl_places"](...)
		route = self.tools["transit"](...)

		return self.synthesize(
			intent=intent,
			dates=dates,
			weather=weather,
			hotel=hotel_candidates,
			places=place_candidates,
			route=route,
		)
```

발표용 핵심 문장:

"이 프로젝트는 LLM 하나에 모든 걸 맡기지 않고, 의도 추출, 날짜 최적화, 날씨 조회, 숙소 검색, 장소 검색, 동선 계산을 각각의 tool과 외부 API로 분해한 뒤 마지막에 합성하는 구조입니다."
months=intent.target_months,

## 4. 자연어를 바로 실행 가능한 상태로 바꾸는 의도 추출

    							is_nonstop=intent.prefer_nonstop,
    					)[0]

    			weather = self.tools["weather"](...)
    			hotel_candidates = self.tools["hotel"](...)
    			place_candidates = self.tools["domestic_places"](...) if intent.is_domestic else self.tools["intl_places"](...)
    			route = self.tools["transit"](...)

    			return self.api.synthesize(
    					intent=intent,
    					dates=dates,
    					weather=weather,
    					hotel=hotel_candidates,
    					places=place_candidates,
    					route=route,
    			)

```

발표용 핵심 문장:

"이 프로젝트는 LLM 하나에 모든 걸 맡기지 않고, 의도 추출, 날짜 최적화, 날씨 조회, 숙소 검색, 장소 검색, 동선 계산을 각각의 tool로 분해한 뒤 마지막에 합성하는 구조입니다."

## 4. 자연어를 바로 실행 가능한 상태로 바꾸는 의도 추출

첫 번째 강점은 사용자의 자연어를 단순 요약하지 않고, 실제 실행 가능한 상태로 변환한다는 점입니다. `src/agent/nodes/intent_router.py`에서는 사용자의 메시지에서 목적지, 체크인/체크아웃, 예산, 인원, 여행 일수, 선호 호텔, 직항 선호 같은 정보를 구조화해서 `TravelIntent`로 만듭니다.

특히 좋은 점은 날짜를 두 가지 상태로 나눠 처리한다는 것입니다.

- 날짜가 정확히 정해졌으면 바로 후속 노드로 진행합니다.
- "7월쯤", "여름에", "미정"처럼 날짜가 유동적이면 날짜 최적화 노드로 넘깁니다.

이 구조는 발표에서 매우 중요합니다. 대부분의 데모는 사용자가 날짜를 정확히 입력해야만 작동하지만, 이 프로젝트는 애초에 모호한 사용자 요구를 전제로 설계되어 있습니다. 즉, 에이전트가 "정보가 덜 주어졌을 때 어떻게 보완할 것인가"까지 처리합니다.

말하기 좋은 문장:

"사용자 입력을 그냥 텍스트로 두지 않고, 다음 단계가 바로 소비할 수 있는 여행 명세서로 바꿉니다. 이게 에이전트의 출발점입니다."

## 5. 날짜 미정 상황을 '추천 문제'로 바꾸는 설계

이 프로젝트의 차별점 중 하나는 날짜가 정해지지 않았을 때도 서비스를 멈추지 않는다는 점입니다. `src/agent/nodes/date_optimizer.py`는 항공권 최저가와 날씨를 함께 고려해 여행 날짜 후보를 평가합니다.

여기서 중요한 것은 단순 최저가 검색이 아니라, 여러 점수를 합쳐 최적 날짜를 고른다는 점입니다.

- 맑은 날씨에 점수를 줍니다.
- 적정 기온 범위를 반영합니다.
- 강수 확률이 낮을수록 유리하게 봅니다.
- 항공권 가격도 점수에 포함합니다.

즉, 사용자가 "언제 갈지 모르겠다"고 말해도 시스템은 자동으로 후보를 만들고, 그 후보들 중 가장 합리적인 선택지를 제안합니다. 이건 단순 검색이 아니라 의사결정 지원입니다.

발표에서 강조할 포인트:

- "날짜 미정"을 실패로 처리하지 않고, 추천 문제로 바꿉니다.
- 가격과 날씨를 같이 보므로 실제 여행 의사결정에 가깝습니다.
- 항공권이 없을 때도 날씨만으로 fallback 추천이 가능합니다.

말하기 좋은 문장:

"사용자가 날짜를 못 정했을 때도 서비스는 멈추지 않습니다. 오히려 그 상황을 가장 값비싼 의사결정 문제로 보고, 항공권과 날씨를 함께 최적화합니다."

## 6. 날씨를 단순 조회가 아니라 여행 조건으로 사용

날씨는 단순 정보 출력이 아니라 후속 추천의 조건으로 쓰입니다. `src/agent/nodes/weather_node.py`와 `src/weather` 계열 코드를 보면, 날씨는 여행 기간 전체를 기준으로 수집되고, 우천 여부는 장소 검색 분기에 영향을 줍니다.

이 부분의 강점은 두 가지입니다.

첫째, 날짜 범위별로 다른 데이터를 씁니다.

- 과거 날짜는 아카이브 데이터를 사용합니다.
- 가까운 미래는 예보를 사용합니다.
- 더 먼 미래는 시즌 예보를 사용합니다.

둘째, 날씨 결과가 다음 노드의 쿼리 전략에 반영됩니다. 비가 오면 실내 명소를 더 우선하도록 검색 방향이 바뀝니다. 즉, 날씨가 정보에 그치지 않고 실제 추천 로직을 바꾸는 변수로 작동합니다.

발표용 포인트:

- 같은 날씨 API라도 시점에 따라 다른 데이터를 써서 정확도를 높입니다.
- 우천 여부가 검색 키워드와 장소 구성에 반영됩니다.
- 여행 추천에서 가장 중요한 "오늘 날씨에 맞는 동선"을 시스템이 직접 고려합니다.

말하기 좋은 문장:

"날씨는 보여주기용 데이터가 아니라, 장소 추천을 바꾸는 실제 조건입니다. 비가 오면 실내 코스가 앞에 오고, 맑으면 실외 코스가 살아납니다."

## 7. 숙소를 '검색'이 아니라 '예산 배분'의 문제로 다룸

`src/agent/nodes/stay_node.py`는 숙소 검색을 단순 목록 조회로 끝내지 않습니다. 총 예산, 항공권 비용, 숙박 일수까지 고려해서 1박당 허용 금액을 계산한 뒤, 그 범위 안에서 숙소 후보를 고릅니다.

이것이 강한 이유는 여행 계획에서 숙소가 단순한 옵션이 아니라 전체 예산 구조를 결정하는 핵심 항목이기 때문입니다.

코드상으로도 다음 특징이 있습니다.

- 호텔 선호 조건을 별도 interrupt로 받습니다.
- 정렬 기준, 별점, 등급, 조식, 수영장, 무료 취소 같은 현실적인 필터를 사용합니다.
- API가 없거나 실패해도 mock 데이터를 반환해 데모가 끊기지 않습니다.
- 사용자가 특정 호텔명을 직접 말한 경우에는 그 호텔을 우회적으로 바로 사용합니다.

발표에서 강조하면 좋은 문장:

"숙소는 단순히 좋은 곳을 찾는 게 아니라, 전체 예산을 어떤 비율로 배분할지 결정하는 단계로 설계했습니다. 그래서 추천이 더 현실적입니다."

## 8. 국내/해외를 자동 분기하는 장소 검색 엔진

`src/agent/nodes/place_node.py`는 이 프로젝트의 멀티 API 통합 강점을 가장 잘 보여주는 부분입니다. 목적지가 국내인지 해외인지 판단한 뒤, 국내면 Naver Local Search API, 해외면 Google Places API를 사용합니다.

이건 발표에서 꼭 강조할 만합니다. 보통은 하나의 검색 API만 붙이지만, 이 프로젝트는 지역에 따라 더 적합한 API를 골라 씁니다. 즉, "모든 상황을 하나의 도구로 처리하는 게 아니라, 상황에 맞는 tool을 선택하는 에이전트"라는 설계입니다.

추가로 이 노드는 다음과 같은 장점을 가집니다.

- 날씨가 좋지 않으면 실내 중심 쿼리로 바뀝니다.
- 식당과 명소를 따로 병렬 수집합니다.
- 중복 제거와 LLM 큐레이션을 통해 후보를 정제합니다.
- API 실패 시 mock 후보로 대체해 데모 안정성을 확보합니다.

발표용 포인트:

- 국내와 해외를 다른 데이터 소스로 처리하는 것은 현실적인 설계입니다.
- 비가 오면 "관광지" 대신 "실내 명소"를 찾는 식으로 검색 문맥이 바뀝니다.
- 후보를 많이 모은 뒤, LLM이 최종적으로 골라내므로 검색과 판단이 분리됩니다.

말하기 좋은 문장:

"장소 검색은 단순한 키워드 검색이 아니라, 국내외 구분·날씨·예산을 반영하는 검색 전략입니다. 그래서 같은 여행 요청이라도 조건에 따라 결과가 달라집니다."

## 9. 동선을 계산해서 일정의 품질을 올림

이 프로젝트가 단순 추천을 넘어서는 이유는 `place_node` 안에서 실제 좌표를 확보하고, 그 좌표를 바탕으로 이동 동선을 최적화하기 때문입니다. 최근접 이웃 방식으로 숙소 기준의 방문 순서를 정하고, 각 장소 간 이동 거리를 계산해서 `route_note`를 만듭니다.

이 기능의 의미는 분명합니다.

- 장소가 예쁘기만 한 일정이 아니라 실제로 움직일 수 있는 일정이 됩니다.
- 사용자가 체감하는 품질이 "어디를 가느냐"에서 "어떻게 이동하느냐"로 확장됩니다.
- 여행 추천에서 자주 빠지는 실전 요소인 동선 최적화를 코드로 구현했습니다.

발표에서 이렇게 말할 수 있습니다.

"추천 AI가 진짜 여행 플래너가 되려면 장소 목록만 주면 안 됩니다. 이동 순서와 거리까지 계산해야 하고, 이 프로젝트는 그 부분까지 코드로 처리합니다."

## 10. 최종 결과는 마크다운 일정표로 바로 사용할 수 있게 생성

`src/agent/nodes/synthesizer_node.py`는 수집된 숙소, 맛집, 명소, 날씨, 예산 정보를 LLM에 넘겨 최종 마크다운 일정표를 생성합니다. 단순한 텍스트 응답이 아니라, 발표 자료나 실제 여행 문서로 바로 옮길 수 있는 형태로 결과를 만듭니다.

여기서 중요한 점은 출력 형식을 강하게 통제한다는 것입니다.

- 한국어로 출력합니다.
- GFM 표 형식을 강제합니다.
- 시간, 장소, 활동, 이동, 비고 같은 항목이 구조적으로 정리됩니다.
- 존재하지 않는 장소나 비용을 임의로 만들지 않도록 제한합니다.

즉, LLM이 자유롭게 글을 쓰는 것이 아니라, 정해진 틀 안에서 여행 계획서를 작성하도록 유도합니다. 이 부분은 신뢰성 측면에서 강점입니다.

발표용 문장:

"최종 답변은 그냥 채팅 메시지가 아니라, 바로 읽고 실행할 수 있는 여행 일정표입니다. LLM의 창의성은 살리되, 출력 형식은 엄격하게 통제했습니다."

## 11. interrupt / resume 구조로 실제 대화형 에이전트를 구현

이 프로젝트는 한 번에 끝나는 배치형 처리보다, 사용자의 추가 선택을 받는 대화형 에이전트에 가깝습니다. `api/routes/plan.py`를 보면 `/plan/start`와 `/plan/resume`가 따로 있고, LangGraph의 interrupt와 Command resume을 사용합니다.

이 구조의 장점은 다음과 같습니다.

- 날짜 선택이 필요한 경우 사용자에게 후보를 보여주고 다시 받습니다.
- 호텔 조건을 먼저 묻고, 그 다음 후보를 추리는 흐름이 가능합니다.
- 중간 단계에서 다시 묻는 방식이어서 사용자 경험이 자연스럽습니다.
- 체크포인트를 사용해 상태를 유지하므로 재개가 가능합니다.

발표에서 이 부분은 꼭 기술적으로 보일 수 있습니다. "에이전트가 중간에 멈추고, 사용자의 선택으로 다시 이어진다"는 점은 데모 임팩트가 큽니다.

말하기 좋은 문장:

"이 시스템은 질문을 다 끝낸 다음 답하는 구조가 아니라, 사용자의 선택을 끼워 넣으면서 같이 완성되는 대화형 에이전트입니다."

## 12. API를 많이 붙였지만, 코드 구조는 역할별로 잘 분리됨

이 프로젝트는 여러 외부 API를 연결했지만, 코드가 한 곳에 뒤엉켜 있지 않습니다. `src/agent/nodes/`는 역할별로 분리돼 있고, `src/tools/`는 tool 정의를 따로 두고 있으며, `api/routes/plan.py`는 HTTP 인터페이스만 담당합니다.

즉, 구조가 다음처럼 나뉘어 있습니다.

- `agent`는 추론과 흐름 제어를 담당합니다.
- `weather`, `hotel`, `tourist`, `transport`, `cheapest_date`는 실제 데이터 수집을 담당합니다.
- `api`는 사용자와 에이전트 사이의 입출력만 담당합니다.
- 프론트엔드는 진행 상태와 상호작용을 시각화합니다.

이렇게 나누면 장점이 큽니다.

- 각 기능을 독립적으로 교체할 수 있습니다.
- 한 API가 실패해도 다른 영역을 수정하기 쉽습니다.
- 발표할 때도 "모듈형 에이전트"라고 설명하기 좋습니다.

말하기 좋은 문장:

"외부 API를 많이 붙였지만, 핵심은 복잡함을 한곳에 모으지 않고 역할별로 나눈 구조입니다. 그래서 확장하기 쉽고, 시연도 안정적입니다."

## 13. 실패해도 멈추지 않는 폴백 전략

실제 서비스 데모에서는 API 실패가 자주 문제입니다. 이 프로젝트는 그 부분을 꽤 의식적으로 처리합니다.

- 호텔 검색이 실패하면 mock 데이터를 반환합니다.
- 장소 검색이 실패해도 mock 후보로 대체합니다.
- 날씨나 좌표 검색도 예외 처리로 서비스 전체가 멈추지 않게 설계되어 있습니다.
- SSE 스트림과 단계 상태 UI가 있어서 진행 상황을 보여줄 수 있습니다.

이런 폴백은 발표에서 매우 중요한 강점입니다. 단순히 "많은 기능이 있다"보다, "실제로 끝까지 돌아가도록 설계했다"는 인상을 줍니다.

말하기 좋은 문장:

"데모에서 중요한 건 기능 수가 아니라 안정성입니다. 이 프로젝트는 각 단계에 fallback을 두어, 외부 API 변동이 있어도 전체 흐름이 무너지지 않게 만들었습니다."

## 14. 프론트엔드에서 에이전트 과정을 보여주는 구성

`lovable/src/components/travel/TravelPlannerApp.tsx`를 보면, 단순히 결과만 보여주는 UI가 아니라 에이전트의 진행 단계를 단계별로 보여주는 구조입니다.

장점은 다음과 같습니다.

- 사용자는 AI가 지금 무엇을 하는지 볼 수 있습니다.
- 날짜 선택, 숙소 조건, 숙소 선택 같은 중간 단계가 자연스럽게 드러납니다.
- Orchestrator, Date Optimizer, Stay Agent, Place & Dining, Routing Optimizer, Synthesizer처럼 파이프라인이 시각적으로 보입니다.

이건 발표에서 시각적 설득력이 큽니다. 관객이 결과만 보는 것이 아니라, 에이전트의 내부 작업 순서를 이해하게 되기 때문입니다.

## 15. 발표에서 가장 강하게 들리는 핵심 메시지

이 프로젝트는 "여행 추천"이 아니라 "여행 계획을 만드는 AI 워크플로우"입니다.

강조하면 좋은 핵심 메시지는 세 가지입니다.

1. 사용자의 모호한 요청을 구조화된 여행 상태로 바꿉니다.
2. 날짜, 날씨, 예산, 숙소, 장소, 동선을 여러 API와 규칙으로 연결합니다.
3. 최종 결과를 읽기 쉬운 일정표로 합성해 실제 사용 가능한 형태로 제공합니다.

## 16. 발표 스크립트용 문단

아래 문단은 발표에서 거의 그대로 읽어도 됩니다.

"이 프로젝트의 핵심은 단순한 챗봇이 아니라, 여행 계획을 실제로 조립하는 에이전트라는 점입니다. 사용자가 한 문장으로 목적지와 일정의 힌트만 주더라도, 시스템은 그 요청을 목적지, 날짜, 예산, 인원 같은 구조화된 정보로 바꾸고, 그 다음 단계에서 날씨, 숙소, 장소, 동선까지 순차적으로 계산합니다."

"특히 날짜가 정해지지 않은 경우에도 멈추지 않는다는 점이 중요합니다. 보통은 입력이 부족하면 실패하지만, 우리는 그 상황을 날짜 최적화 문제로 바꿔서 항공권과 날씨를 함께 평가합니다. 즉, 에이전트가 단순히 답변을 생성하는 것이 아니라, 사용자의 결정을 도와주는 쪽으로 동작합니다."

"또한 국내와 해외를 구분해서 Naver와 Google Places를 다르게 사용하고, 비가 오면 실내 위주의 검색으로 전환하며, 숙소와 예산, 동선까지 함께 고려합니다. 그래서 이 시스템은 검색 도구들의 모음이 아니라, 실제 여행 계획을 만들어내는 분산형 에이전트 파이프라인이라고 볼 수 있습니다."

"마지막으로 결과는 마크다운 일정표로 출력되어 바로 읽고 활용할 수 있습니다. 즉, 이 프로젝트는 LLM의 생성 능력과 외부 API의 정확성, 그리고 워크플로우 설계를 하나로 묶어낸 여행 계획 에이전트입니다."

## 17. 짧은 요약 문구

- 자연어 여행 요청을 실행 가능한 여행 일정으로 바꾸는 AI 에이전트
- 날짜 미정, 날씨 변수, 예산 제약까지 반영하는 다단계 플래너
- 국내/해외를 구분해 API를 선택하고, 결과를 동선까지 최적화하는 여행 설계 엔진
- interrupt / resume 기반의 대화형 LangGraph 워크플로우
- 실패해도 멈추지 않는 폴백 중심의 데모 친화 구조
```
