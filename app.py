from __future__ import annotations

import os
import subprocess
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

VALHALLA_URL = "http://127.0.0.1:8002"
CONFIG = os.environ.get("VALHALLA_CONFIG", "/tmp/valhalla/tiles/valhalla.json")
_process: subprocess.Popen[str] | None = None


class Point(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class MatrixRequest(BaseModel):
    new_point: Point
    existing_points: list[Point] = Field(min_length=1, max_length=500)
    costing: str = "auto"


def _matrix(sources: list[Point], targets: list[Point], costing: str) -> dict:
    payload = {
        "sources": [p.model_dump() for p in sources],
        "targets": [p.model_dump() for p in targets],
        "costing": costing,
        "units": "kilometers",
    }
    response = httpx.post(f"{VALHALLA_URL}/sources_to_targets", json=payload, timeout=30)
    if response.is_error:
        raise HTTPException(response.status_code, response.text)
    return response.json()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _process
    command = ["/tmp/valhalla/bin/valhalla_service", CONFIG, "1"]
    env = os.environ | {"LD_LIBRARY_PATH": "/tmp/valhalla/lib"}
    _process = subprocess.Popen(command, env=env, text=True)
    for _ in range(60):
        try:
            if httpx.get(f"{VALHALLA_URL}/status", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(1)
    else:
        raise RuntimeError("Valhalla did not become ready")
    yield
    _process.terminate()
    _process.wait(timeout=10)


app = FastAPI(title="Valhalla Matrix POC", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    response = httpx.get(f"{VALHALLA_URL}/status", timeout=2)
    return {"status": "ok", "valhalla": response.json()}


@app.post("/augment-matrix")
def augment_matrix(request: MatrixRequest) -> dict:
    # Road travel is asymmetric, so an inserted matrix row and column are both returned.
    outbound = _matrix([request.new_point], request.existing_points, request.costing)
    inbound = _matrix(request.existing_points, [request.new_point], request.costing)
    return {"from_new": outbound["sources_to_targets"][0], "to_new": [row[0] for row in inbound["sources_to_targets"]]}
