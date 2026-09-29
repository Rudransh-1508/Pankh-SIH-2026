from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.applications.router import router as applications_router
from app.auth.router import router as auth_router
from app.authoring.router import router as authoring_router
from app.chasing.router import router as chasing_router
from app.config import get_settings
from app.coverage.router import router as coverage_router
from app.documents.router import router as documents_router
from app.eligibility.router import router as eligibility_router
from app.facts.router import router as facts_router
from app.family.router import router as family_router
from app.grievance.router import router as grievance_router
from app.jago.router import router as jago_router
from app.letters.router import router as letters_router
from app.outreach.router import router as outreach_router
from app.phone.router import router as phone_router
from app.renewal.router import router as renewal_router
from app.review.router import router as review_router
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
        applications_router,
        review_router,
        coverage_router,
        jago_router,
        chasing_router,
        family_router,
        documents_router,
        outreach_router,
        renewal_router,
        grievance_router,
        phone_router,
        authoring_router,
        letters_router,
    ):
        app.include_router(router, prefix="/v1")

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
