from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.config import get_settings
from app.eligibility.router import router as eligibility_router
from app.facts.router import router as facts_router
from app.schemes.router import router as schemes_router
from app.verification.router import router as verification_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pankh API",
        version="0.1.0",
        summary="Scholarships for Scheduled Tribe students: schemes, eligibility and more.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (
        auth_router,
        facts_router,
        schemes_router,
        eligibility_router,
        verification_router,
    ):
        app.include_router(router, prefix="/v1")

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
