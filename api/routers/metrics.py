from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..auth import require_api_key

router = APIRouter(prefix="/metrics", tags=["metrics"], dependencies=[Depends(require_api_key)])


@router.get("")
def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
