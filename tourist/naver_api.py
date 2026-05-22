import requests

client_id = "3YlmBeosPwYBVAQSR0wk"
client_secret = "KKwRJd0xx2"

# 검색어
query = "해운대 조용한 횟집" 

url = "https://openapi.naver.com/v1/search/local.json"
params = {"query": query, "display": 5}
headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}

response = requests.get(url, headers=headers, params=params)
print(response.json())