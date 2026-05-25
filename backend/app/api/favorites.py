from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.core.database import get_db
from app.services.vehicle_service import get_favorites, add_favorite, remove_favorite
import uuid

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _get_session_id(x_session_id: Optional[str] = Header(None)) -> str:
    if not x_session_id:
        return str(uuid.uuid4())
    return x_session_id


@router.get("")
async def list_favorites(
    session_id: str = Depends(_get_session_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_favorites(db, session_id)


@router.post("/{vehicle_id}")
async def toggle_favorite_add(
    vehicle_id: int,
    session_id: str = Depends(_get_session_id),
    db: AsyncSession = Depends(get_db),
):
    result = await add_favorite(db, session_id, vehicle_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Já favoritado ou veículo não encontrado")
    return {"message": "Adicionado aos favoritos", "id": result.id}


@router.delete("/{vehicle_id}")
async def remove_favorite_route(
    vehicle_id: int,
    session_id: str = Depends(_get_session_id),
    db: AsyncSession = Depends(get_db),
):
    success = await remove_favorite(db, session_id, vehicle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorito não encontrado")
    return {"message": "Removido dos favoritos"}
