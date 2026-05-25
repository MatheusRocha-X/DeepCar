from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.schemas import VehicleResponse
from app.services.vehicle_service import get_vehicle_by_id

router = APIRouter(prefix="/car", tags=["vehicles"])


@router.get("/{vehicle_id}")
async def get_car(vehicle_id: int, db: AsyncSession = Depends(get_db)):
    vehicle = await get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return vehicle
