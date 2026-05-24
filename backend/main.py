import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.tech import router as tech_router
from routers.policy import router as policy_router
from routers.industry import router as industry_router
from routers.llm import router as llm_router
from routers.scrape import router as scrape_router
from routers.market import router as market_router
from scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("techpolicy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting, scheduler=%s", settings.scheduler_enabled)
    start_scheduler()
    yield
    logger.info("Application shutting down")
    shutdown_scheduler()


app = FastAPI(title="TechPolicy Dashboard API", lifespan=lifespan)

cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(tech_router, prefix="/api")
app.include_router(policy_router, prefix="/api")
app.include_router(industry_router, prefix="/api")
app.include_router(llm_router, prefix="/api")
app.include_router(scrape_router, prefix="/api")
app.include_router(market_router, prefix="/api")
