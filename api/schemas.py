from pydantic import BaseModel


class PlanRequest(BaseModel):
    message: str
    budget: str | None = None
    people: str | None = None
    stay: str | None = None


class PlaceItem(BaseModel):
    title: str
    address: str
    category: str
    description: str = ""


class PlanResponse(BaseModel):
    intent: dict
    weather_summary: str
    hotel_name: str
    hotel_address: str
    hotel_cost: int
    remaining_budget: int
    restaurants: list[PlaceItem]
    attractions: list[PlaceItem]
    final_report: str


class ResumeRequest(BaseModel):
    thread_id: str
    choice: str  # "1", "2", "3"


class StartPlanResponse(BaseModel):
    thread_id: str
    phase: str  # "date_selection" | "hotel_selection" | "done"
    question: str | None = None
    candidates: list[dict] | None = None
    result: PlanResponse | None = None
