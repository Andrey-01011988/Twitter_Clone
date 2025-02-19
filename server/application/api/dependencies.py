import hashlib
import logging
from typing import Union

from fastapi import Header, HTTPException, Depends

from application.crud import BaseDAO
from application.database import AsyncSessionApp
from application.models import Users, Tweets, Media, Like, Followers
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Здесь добавь функцию хеширования данных
async def hash_password(some_password):
    return hashlib.sha256(some_password.encode()).hexdigest()


# Назначение текущей сессии
async def get_current_session() -> AsyncSession:
    """
    Создает и управляет текущей сессией базы данных.

    Эта функция создает новую асинхронную сессию базы данных и передает ее
    вызывающим функциям. Сессия будет закрыта после завершения использования.

    :return: Асинхронная сессия базы данных (AsyncSession).
    """
    logger.info("Создание новой сессии Dependencies")
    async with AsyncSessionApp() as current_session:
        try:
            logger.info("Передача сессии session: %s", current_session)
            yield current_session
        finally:
            logger.info("Закрывается сессия session: %s", current_session)
            await current_session.close()
            logger.info("Закрытие сессии Dependencies")


async def get_client_token(
    session: AsyncSession = Depends(get_current_session), api_key: str = Header(...)
):
    """
    Извлекает API ключ из заголовка и проверяет его на валидность.

    :param session:
    :param api_key: API ключ пользователя
    :return: API ключ, если он валиден
    """
    # Здесь должен быть перевод api_key в hash и сравнение его с хранимой в базе данных информацией
    if api_key == "my_api":
        api_key = await hash_password(api_key)
    user = await UserDAO.find_one_or_none(api_key=api_key, session=session)
    logger.info("Пользователь найден: %s", user)
    if user is None:
        raise HTTPException(
            status_code=403, detail="Доступ запрещен: неверный API ключ"
        )
    logger.info("Возвращен ключ api_key: %s", api_key)
    return api_key


# Зависимость для получения текущего пользователя
async def get_current_user(
    session: AsyncSession = Depends(get_current_session),
    api_key: str = Depends(get_client_token),
) -> Union[Users, JSONResponse]:
    """
    Извлекает текущего пользователя на основе API ключа.

    Эта функция использует переданную сессию и API ключ для поиска
    пользователя в базе данных. Если пользователь не найден, возвращается
    JSONResponse с кодом 404.

    :param session: Асинхронная сессия базы данных (AsyncSession),
                    используемая для выполнения запросов.
    :param api_key: API ключ пользователя, получаемый из заголовка.
    :return: Объект пользователя (Users), если он найден, или
             JSONResponse с ошибкой 404, если пользователь не найден.
    """
    current_user = await UserDAO.find_one_or_none(
        session=session,
        options=[selectinload(Users.authors), selectinload(Users.followers)],
        api_key=api_key,
    )
    if not current_user:
        logger.warning("Пользователь с API ключом %s не найден.", api_key)
        return JSONResponse(status_code=404, content={"error": "User not found"})
    return current_user


class UserDAO(BaseDAO):
    model = Users

    @classmethod
    async def create_user(cls, session: AsyncSession, name:str, api_key:str):
        logger.info("Начало создания нового пользователя")
        api_key = await hash_password(api_key)
        new_user = Users(name=name, api_key=api_key)
        try:
            async with session.begin():
                session.add(new_user)
                await session.commit()
                logger.info("Новый пользователь успешно создан")
                return new_user
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Ошибка при создании нового пользователя: {e}")
            raise e


class TweetDAO(BaseDAO):
    model = Tweets


class MediaDAO(BaseDAO):
    model = Media


class LikeDAO(BaseDAO):
    model = Like


class FollowersDAO(BaseDAO):
    model = Followers
