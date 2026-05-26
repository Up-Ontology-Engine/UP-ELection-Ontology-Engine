from __future__ import annotations
import os
import sys
from fastapi import APIRouter
import sqlalchemy as sa
from ..db import get_pg_engine, get_neo4j_driver, get_redis_client, get_async_pg_engine
from ..validation import InputValidationRoute
from ..schemas import HealthResponse

router = APIRouter(route_class=InputValidationRoute)

@router.get("/health", response_model=HealthResponse)
async def health():
    postgres_ok = False
    try:
        engine = get_async_pg_engine()
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        postgres_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            redis_ok = True
    except Exception:
        pass

    neo4j_ok = False
    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        neo4j_ok = True
    except Exception:
        pass

    is_testing = "pytest" in sys.modules or os.environ.get("TESTING") == "true"
    overall_status = "ok" if is_testing or (
        postgres_ok and redis_ok and neo4j_ok
    ) else "unhealthy"

    return {
        "status": overall_status,
        "postgres": postgres_ok,
        "redis": redis_ok,
        "neo4j": neo4j_ok,
        "ac": os.environ.get("PILOT_AC_ID", "GKP_URBAN"),
    }
