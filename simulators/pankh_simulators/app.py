from fastapi import FastAPI

from pankh_simulators import digilocker, paper, registers, scholarship_systems

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


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
