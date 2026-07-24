from fastapi import APIRouter, Depends

from app.core.security import require_internal_api_key

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/ping", dependencies=[Depends(require_internal_api_key)])
def internal_ping() -> dict[str, str]:
    return {"status": "ok", "scope": "internal"}
