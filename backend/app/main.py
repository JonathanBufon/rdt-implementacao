import asyncio
from contextlib import asynccontextmanager
from queue import Empty
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import Field

from .simulation.network_engine import NetworkEngine

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

engine = NetworkEngine(config_dir=CONFIG_DIR, logs_dir=LOGS_DIR)


class SendMessageRequest(BaseModel):
    source: int
    destination: int
    message: str
    rdt_version: str = "1.0"


class SimulationSettingsRequest(BaseModel):
    loss_rate: float | None = Field(default=None, ge=0, le=1)
    corruption_rate: float | None = Field(default=None, ge=0, le=1)
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_retries: int | None = Field(default=None, ge=1)


class LinkCostRequest(BaseModel):
    source: int
    target: int
    cost: int = Field(gt=0)


class LinkRequest(BaseModel):
    source: int
    target: int


class TopologyLayoutRequest(BaseModel):
    layout: str = "spring"


class RandomTopologyRequest(BaseModel):
    nodes: int = Field(ge=5)
    edges: int = Field(ge=0)
    min_cost: int = Field(default=1, ge=1)
    max_cost: int = Field(default=20, ge=1)
    layout: str = "spring"
    connected: bool = True


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:
    engine.start()
    try:
        yield
    finally:
        engine.stop()

app = FastAPI(
    title="RDT P2P Visualizer API",
    description="Control API for the UDP-based reliable P2P messaging simulator.",
    version="0.1.0",
    lifespan=lifespan,
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
def topology() -> dict[str, object]:
    try:
        return engine.topology().to_api_response()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/routes/{router_id}")
def routes(router_id: int) -> dict[str, int | dict[str, dict[str, int | list[int]]]]:
    try:
        return engine.routing_table(router_id).to_api_response()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/routers")
def routers() -> list[dict[str, int | str]]:
    try:
        return engine.topology().to_api_response()["routers"]
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/messages/send")
def send_message(payload: SendMessageRequest) -> dict[str, int | str | list[int]]:
    try:
        return engine.send_message(
            source=payload.source,
            destination=payload.destination,
            message=payload.message,
            rdt_version=payload.rdt_version,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/simulation/settings")
def simulation_settings() -> dict[str, float | int]:
    return engine.simulation_settings()


@app.patch("/simulation/settings")
def update_simulation_settings(payload: SimulationSettingsRequest) -> dict[str, float | int]:
    return engine.update_simulation_settings(
        loss_rate=payload.loss_rate,
        corruption_rate=payload.corruption_rate,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
    )


@app.patch("/topology/links")
def update_link_cost(payload: LinkCostRequest) -> dict[str, object]:
    try:
        return engine.update_link_cost(
            source=payload.source,
            target=payload.target,
            cost=payload.cost,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/topology/links")
def create_link(payload: LinkCostRequest) -> dict[str, object]:
    try:
        return engine.create_link(
            source=payload.source,
            target=payload.target,
            cost=payload.cost,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/topology/links")
def remove_link(payload: LinkRequest) -> dict[str, object]:
    try:
        return engine.remove_link(
            source=payload.source,
            target=payload.target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/topology/layout")
def update_topology_layout(payload: TopologyLayoutRequest) -> dict[str, object]:
    try:
        return engine.apply_layout(payload.layout)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/topology/random")
def generate_random_topology(payload: RandomTopologyRequest) -> dict[str, object]:
    try:
        return engine.generate_random_topology(
            nodes=payload.nodes,
            edges=payload.edges,
            min_cost=payload.min_cost,
            max_cost=payload.max_cost,
            layout=payload.layout,
            connected=payload.connected,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/logs/{router_id}")
def logs(router_id: int) -> dict[str, int | list[str]]:
    router_ids = {router.id for router in engine.topology().routers}
    if router_id not in router_ids:
        raise HTTPException(status_code=404, detail=f"router {router_id} is not configured")

    return {"router_id": router_id, "lines": engine.read_logs(router_id)}


@app.get("/events")
def events() -> list[dict[str, object]]:
    return engine.recent_events()


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    for event in engine.recent_events():
        await websocket.send_json(event)

    subscriber = engine.subscribe_events()
    try:
        while True:
            try:
                event = await asyncio.to_thread(subscriber.get, True, 1)
            except Empty:
                await websocket.send_json({"type": "HEARTBEAT"})
                continue
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        engine.unsubscribe_events(subscriber)
