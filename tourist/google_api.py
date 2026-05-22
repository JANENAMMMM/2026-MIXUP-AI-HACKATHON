import requests

def test_google_places():
    # 1. API 키 설정 (실제 개발 시에는 .env 파일에 빼두시는 것을 추천합니다!)
    api_key = "AIzaSyC-JhcC6QazYlvxhBbEqJdtFQgqBP5XcKU"
    url = "https://places.googleapis.com/v1/places:searchText"

    # 2. 헤더 및 필드 마스크 설정
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
    }

    # 3. 검색 쿼리 (해외 식당/명소 테스트)
    data = {
        "textQuery": "Tokyo Shibuya Yakitori"
    }

    # 4. API 호출
    print("API 호출 중...\n")
    response = requests.post(url, headers=headers, json=data)

    # 5. 결과 출력
    if response.status_code == 200:
        result = response.json()
        places = result.get("places", [])
        
        print(f"✅ 총 {len(places)}개의 장소를 찾았습니다.\n")
        print("-" * 30)
        
        # JSON에서 필요한 알맹이만 파싱해서 출력하기
        for i, place in enumerate(places, 1):
            # 구글 API는 이름이 displayName 객체 안의 text 필드에 들어있습니다.
            name = place.get("displayName", {}).get("text", "이름 정보 없음")
            address = place.get("formattedAddress", "주소 정보 없음")
            
            print(f"[{i}] {name}")
            print(f" 📍 주소: {address}")
            print("-" * 30)
    else:
        print(f"❌ 에러 발생! 상태 코드: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_google_places()