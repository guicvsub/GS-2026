from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import SPTRANS_BASE_URL, SPTRANS_TOKEN
from app.routes.consulta import router
from app.services.sptrans import SPTransService


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as client:
        app.state.sptrans = SPTransService(client, SPTRANS_BASE_URL, SPTRANS_TOKEN)
        yield


app = FastAPI(
    title="SPTrans Olho Vivo API",
    description="Template mínimo para futuras consultas à API Olho Vivo.",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.sptrans_base_url = SPTRANS_BASE_URL
app.include_router(router)
