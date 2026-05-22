import os
from dotenv import load_dotenv
load_dotenv()

print("=== LangSmith 환경변수 ===")
keys = ["LANGSMITH_TRACING","LANGCHAIN_TRACING_V2","LANGSMITH_API_KEY","LANGCHAIN_API_KEY","LANGSMITH_PROJECT","LANGSMITH_ENDPOINT"]
for k in keys:
    v = os.getenv(k)
    status = "(SET: " + str(v)[:8] + "...)" if v else "(EMPTY)"
    print(k + " = " + status)

print("\n=== 패키지 버전 ===")
import langsmith, langchain_core
import importlib.metadata as meta
print("langsmith:", langsmith.__version__)
print("langchain-core:", langchain_core.__version__)
try:
    print("langgraph:", meta.version("langgraph"))
except Exception:
    print("langgraph: (version unknown)")

print("\n=== LangSmith 연결 테스트 ===")
try:
    from langsmith import Client
    client = Client()
    projects = list(client.list_projects())
    print("연결 성공! 프로젝트 수:", len(projects))
    for p in projects[:5]:
        print("  -", p.name)
except Exception as e:
    print("연결 실패:", type(e).__name__, str(e))

print("\n=== LangChain 콜백 트레이서 확인 ===")
try:
    from langchain_core.tracers.langchain import LangChainTracer
    tracer = LangChainTracer()
    print("LangChainTracer 초기화 성공, project:", tracer.project_name)
except Exception as e:
    print("LangChainTracer 실패:", type(e).__name__, str(e))
