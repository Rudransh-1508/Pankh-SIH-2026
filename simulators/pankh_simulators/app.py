from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from pankh_simulators import cpgrams, digilocker, paper, registers, scholarship_systems

app = FastAPI(
    title="Pankh simulators",
    summary="Stand-ins for DigiLocker, government registers and scholarship systems, "
    "holding synthetic people only.",
    version="0.1.0",
)
app.include_router(digilocker.router)
app.include_router(registers.router)
app.include_router(scholarship_systems.router)
app.include_router(paper.router)
app.include_router(cpgrams.router)


_PHONE = (Path(__file__).parent / "templates" / "phone.html").read_text()


@app.get("/phone", response_class=HTMLResponse, include_in_schema=False)
async def phone() -> str:
    """A browser stand-in for a phone, calling the Pankh phone line's menu."""
    return _PHONE


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
