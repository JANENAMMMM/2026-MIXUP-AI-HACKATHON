import argparse
from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .llm import get_llm
from .nodes import (
    make_intent_router,
    make_date_optimizer_node,
    weather_node,
    make_stay_node,
    place_node,
    make_synthesizer_node,
)


def build_graph(model: str = "solar-pro3", temperature: float = 0.7, interactive: bool = True):
    """6-노드 여행 플래너 LangGraph 그래프.

    날짜 확정:  START → intent_router → weather → stay → place → synthesizer → END
    날짜 미정:  START → intent_router → date_optimizer → weather → stay → place → synthesizer → END

    Args:
        interactive: True(기본) = date_optimizer에서 TOP 10 표시 후 사용자 확인.
                     False = 1위 자동 선택 (FastAPI 서버 모드).
    """
    llm = get_llm(model=model, temperature=temperature)

    def _route_after_intent(state: AgentState) -> str:
        return "weather" if state.get("date_fixed", True) else "date_optimizer"

    graph = StateGraph(AgentState)
    graph.add_node("intent_router", make_intent_router(llm))
    graph.add_node("date_optimizer", make_date_optimizer_node(interactive=interactive))
    graph.add_node("weather", weather_node)
    graph.add_node("stay", make_stay_node())
    graph.add_node("place", place_node)
    graph.add_node("synthesizer", make_synthesizer_node(llm))

    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        _route_after_intent,
        {"weather": "weather", "date_optimizer": "date_optimizer"},
    )
    graph.add_edge("date_optimizer", "weather")
    graph.add_edge("weather", "stay")
    graph.add_edge("stay", "place")
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
