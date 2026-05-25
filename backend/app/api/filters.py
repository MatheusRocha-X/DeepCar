from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.vehicle_service import get_filter_options

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("")
async def list_filters(db: AsyncSession = Depends(get_db)):
    return await get_filter_options(db)
