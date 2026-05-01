from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.config_loader import load_topology

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

app = FastAPI(
    title="RDT P2P Visualizer API",
    description="Control API for the UDP-based reliable P2P messaging simulator.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/topology")
def topology() -> dict[str, list[dict[str, int | str]]]:
    try:
        return load_topology(CONFIG_DIR).to_api_response()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
