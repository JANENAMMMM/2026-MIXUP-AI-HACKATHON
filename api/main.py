from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import plan

app = FastAPI(
    title="AI Travel Planner API",
    description="LangGraph 기반 여행 플래너 백엔드",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
