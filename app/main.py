"""CareAuth AI — FastAPI Application Entry Point"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.seed.seed import seed_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_data()
    yield

app = FastAPI(
    title="CareAuth AI",
    description="AI-Powered Prior Authorization & Documentation Assistant — MVP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — SEC-7: restricted to frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
