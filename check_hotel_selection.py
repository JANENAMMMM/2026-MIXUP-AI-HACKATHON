import importlib.util
import json
import os
import sys
import types
from pathlib import Path

# 환경에 langgraph가 없을 때도 stay_node.py를 확인하기 위해 최소한의 더미 모듈을 추가합니다.
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

langgraph = types.ModuleType("langgraph")
langgraph.types = types.ModuleType("langgraph.types")
langgraph.types.interrupt = lambda value: value
langgraph.graph = types.ModuleType("langgraph.graph")
langgraph.graph.StateGraph = type("StateGraph", (), {})
langgraph.graph.START = object()
langgraph.graph.END = object()
langgraph.graph.message = types.ModuleType("langgraph.graph.message")
langgraph.graph.message.add_messages = lambda *args, **kwargs: None
sys.modules["langgraph"] = langgraph
sys.modules["langgraph.types"] = langgraph.types
sys.modules["langgraph.graph"] = langgraph.graph
sys.modules["langgraph.graph.message"] = langgraph.graph.message

src_pkg = types.ModuleType("src")
src_pkg.__path__ = [str(root / "src")]
src_agent_pkg = types.ModuleType("src.agent")
src_agent_pkg.__path__ = [str(root / "src" / "agent")]
src_hotel_pkg = types.ModuleType("src.hotel")
src_hotel_pkg.__path__ = [str(root / "src" / "hotel")]
sys.modules["src"] = src_pkg
sys.modules["src.agent"] = src_agent_pkg
sys.modules["src.hotel"] = src_hotel_pkg

state_path = root / "src" / "agent" / "state.py"
state_spec = importlib.util.spec_from_file_location("src.agent.state", state_path)
state_module = importlib.util.module_from_spec(state_spec)
assert state_spec and state_spec.loader
state_spec.loader.exec_module(state_module)
sys.modules["src.agent.state"] = state_module
setattr(src_agent_pkg, "state", state_module)

module_path = root / "src" / "agent" / "nodes" / "stay_node.py"
spec = importlib.util.spec_from_file_location("stay_node", module_path)
stay_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(stay_module)

_search_top3 = stay_module._search_top3


def main() -> None:
    intent = {
        "destination": "Osaka",
        "check_in": "2026-06-01",
        "check_out": "2026-06-03",
        "adults": 2,
        "budget": 1000000,
        "trip_nights": 2,
    }

    max_per_night = int(intent["budget"] * 0.6 // max(intent.get("trip_nights", 1), 1))
    print("숙소 확인 코드 실행")
    print(f"  destination: {intent['destination']}")
    print(f"  check_in: {intent['check_in']}, check_out: {intent['check_out']}")
    print(f"  adults: {intent['adults']}, budget: {intent['budget']:,}원")
    print(f"  예상 1박 최대 예산: {max_per_night:,}원")

    if not os.getenv("SERPAPI_KEY"):
        print("  ⚠️ SERPAPI_KEY가 설정되지 않았습니다. Mock 데이터를 사용합니다.")

    candidates = _search_top3(intent, max_per_night)

    print("\n검색 결과 후보:")
    print(json.dumps(candidates, indent=2, ensure_ascii=False))

    expected_keys = {
        "name",
        "address",
        "description",
        "image_url",
        "cost",
        "rating",
        "amenities",
        "details_link",
    }

    for idx, candidate in enumerate(candidates, start=1):
        missing = expected_keys - set(candidate.keys())
        print(f"\n후보 {idx}:")
        for key in sorted(candidate.keys()):
            print(f"  {key}: {candidate[key]}")
        if missing:
            print(f"  ⚠️ 누락된 필드: {sorted(missing)}")
        else:
            print("  ✅ 모든 예상 필드가 포함되어 있습니다.")

    if candidates and all(expected_keys <= set(c.keys()) for c in candidates):
        print("\n✅ 숙소 후보 출력 구조가 정상입니다.")
    else:
        print("\n⚠️ 숙소 후보 출력 구조에 누락된 항목이 있습니다.")


if __name__ == "__main__":
    main()
