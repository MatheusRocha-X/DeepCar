from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        from app.models import vehicle, favorite
        await conn.run_sync(Base.metadata.create_all)
        added_columns = await conn.run_sync(_ensure_vehicle_columns)
        return {"vehicle_columns_added": added_columns}


def _ensure_vehicle_columns(sync_conn) -> list[str]:
    inspector = inspect(sync_conn)
    columns = {column["name"] for column in inspector.get_columns("vehicles")}
    added_columns: list[str] = []
    required_columns = {
        "possui_passagem_leilao": "ALTER TABLE vehicles ADD COLUMN possui_passagem_leilao BOOLEAN NOT NULL DEFAULT FALSE",
        "valor_referente_entrada": "ALTER TABLE vehicles ADD COLUMN valor_referente_entrada BOOLEAN NOT NULL DEFAULT FALSE",
        "preco_suspeito": "ALTER TABLE vehicles ADD COLUMN preco_suspeito BOOLEAN NOT NULL DEFAULT FALSE",
    }

    for column_name, ddl in required_columns.items():
        if column_name in columns:
            continue
        sync_conn.execute(text(ddl))
        added_columns.append(column_name)

    sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vehicles_possui_passagem_leilao ON vehicles (possui_passagem_leilao)"))
    sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vehicles_valor_referente_entrada ON vehicles (valor_referente_entrada)"))
    sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vehicles_preco_suspeito ON vehicles (preco_suspeito)"))

    return added_columns
