import argparse
from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .llm import get_llm
from .nodes import (
    make_intent_router,
    make_date_compute_node,
    make_date_select_node,
    weather_node,
    make_hotel_compute_node,
    make_hotel_select_node,
    place_node,
    make_synthesizer_node,
)


def build_graph(model: str = "solar-pro3", temperature: float = 0.7):
    """8-노드 여행 플래너 LangGraph 그래프.

    모든 경우:
      START → intent_router → date_compute
                                ├─(후보 있음)→ date_select → weather
                                └─(후보 없음)→ weather
      weather → hotel_compute
                  ├─(선호 호텔)→ place
                  └─(검색 필요)→ hotel_select → place
      place → synthesizer → END

    date_compute와 hotel_compute는 interrupt 없이 API 호출만 수행한다.
    date_select와 hotel_select는 state에서 읽어 interrupt만 발생시키므로
    LangGraph resume 시 재실행돼도 API 이중 호출이 발생하지 않는다.
    """
    llm = get_llm(model=model, temperature=temperature)

    def _route_after_date_compute(state: AgentState) -> str:
        return "date_select" if state.get("candidate_dates") else "weather"

    def _route_after_hotel_compute(state: AgentState) -> str:
        return "place" if state.get("hotel_name") else "hotel_select"

    graph = StateGraph(AgentState)
    graph.add_node("intent_router", make_intent_router(llm))
    graph.add_node("date_compute", make_date_compute_node())
    graph.add_node("date_select", make_date_select_node())
    graph.add_node("weather", weather_node)
    graph.add_node("hotel_compute", make_hotel_compute_node())
    graph.add_node("hotel_select", make_hotel_select_node())
    graph.add_node("place", place_node)
    graph.add_node("synthesizer", make_synthesizer_node(llm))

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "date_compute")
    graph.add_conditional_edges(
        "date_compute",
        _route_after_date_compute,
        {"date_select": "date_select", "weather": "weather"},
    )
    graph.add_edge("date_select", "weather")
    graph.add_edge("weather", "hotel_compute")
    graph.add_conditional_edges(
        "hotel_compute",
        _route_after_hotel_compute,
        {"hotel_select": "hotel_select", "place": "place"},
    )
    graph.add_edge("hotel_select", "place")
    graph.add_edge("place", "synthesizer")
    graph.add_edge("synthesizer", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


def _save_mermaid_image(output_path: Path) -> Path:
    """그래프를 Mermaid PNG 이미지로 저장한다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    app = build_graph()
    app.get_graph().draw_mermaid_png(output_file_path=str(output_path))
    return output_path


if __name__ == "__main__":
    def _load_project_env() -> None:
        """프로젝트 루트의 .env 파일을 로드한다."""
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
    _load_project_env()
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Render the agent graph as a Mermaid PNG.")
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "graph.png",
        help="Output PNG path (default: project root / graph.png)",
    )
    args = parser.parse_args()

    saved_path = _save_mermaid_image(args.output)
    print(f"Saved Mermaid graph image to {saved_path}")
