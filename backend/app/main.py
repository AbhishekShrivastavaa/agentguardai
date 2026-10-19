from contextlib import asynccontextmanager
import os
from app.policies import policy_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models
from app.events import router as events_router
from app.gateway import router as gateway_router
from app.auth_routes import router as auth_router
from app.ai_provider import GROQ_API_KEY, GROQ_MODEL
from app.inventory import router as inventory_router
from app.action_gateway import router as action_gateway_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables when the application starts
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AgentGuard AI",
    description="AI Security Gateway and Threat Monitoring Platform",
    version="1.0.0",
    lifespan=lifespan,
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ] + frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gateway_router)
app.include_router(events_router)
app.include_router(policy_router)
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(action_gateway_router)

@app.get("/")
def home():
    return {
        "project": "AgentGuard AI",
        "status": "running",
        "message": "AI Security Gateway is online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "ai_provider": {
            "configured": bool(GROQ_API_KEY),
            "provider": "Groq",
            "model": GROQ_MODEL,
        },
    }


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }
