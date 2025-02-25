import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env.prod'))
load_dotenv(dotenv_path=dotenv_path)

db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")

DATABASE_URL = (
    f"postgresql+asyncpg://{db_user}:{db_password}@postgres_container:5432/{db_name}"  # for containers
)

proj_engine = create_async_engine(DATABASE_URL)
AsyncSessionApp = async_sessionmaker(
    proj_engine, class_=AsyncSession, expire_on_commit=False
)
