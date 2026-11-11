import httpx
from fastapi import APIRouter, Request

from app.config import SPTRANS_TOKEN
router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sptrans/status")
async def sptrans_status(request: Request) -> dict[str, object]:
    if not SPTRANS_TOKEN:
        return {
            "configured": False,
            "authenticated": False,
            "message": "SPTRANS_TOKEN não configurado no arquivo .env.",
        }

    service = request.app.state.sptrans

    try:
        authenticated = await service.authenticate()
        return {
            "configured": True,
            "authenticated": authenticated,
            "message": "Autenticação realizada." if authenticated else "A SPTrans recusou a autenticação.",
        }
    except httpx.HTTPStatusError as exc:
        return {
            "configured": True,
            "authenticated": False,
            "message": f"A SPTrans respondeu com HTTP {exc.response.status_code}.",
        }
    except httpx.RequestError:
        return {
            "configured": True,
            "authenticated": False,
            "message": "Não foi possível conectar à API da SPTrans por HTTPS.",
        }
