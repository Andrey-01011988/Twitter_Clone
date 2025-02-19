import logging

from typing import List, Dict, Union, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from application.api.dependencies import (
    get_current_session,
    UserDAO,
    FollowersDAO,
    get_client_token,
    get_current_user,
)
from application.models import Users, Tweets, Like
from application.schemas import (
    UserOut,
    ErrorResponse,
    SimpleUserOut,
    UserIn,
)
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


users_router = APIRouter(prefix="/api", tags=["Users"])


@users_router.get("/all_users", response_model=List[SimpleUserOut])
async def get_all_users(
    session: AsyncSession = Depends(get_current_session),
) -> List[Users]:
    """
    Выводит всех пользователей.

    Этот эндпоинт возвращает список всех пользователей из базы данных.

    Пример запроса:
        curl -i GET "http://localhost:8000/api/all_users"

    Для запуска в docker-compose:
        curl -i GET "http://localhost:5000/api/all_users"

    Аргументы:
        session (AsyncSession): Асинхронная сессия SQLAlchemy.

    Возвращает:
        Список пользователей.
    """
    result = await UserDAO.find_all(session=session)
    return result


@users_router.get(
    "/users/me",
    response_model=Dict[str, Union[bool, UserOut]],
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def get_user_info(
    current_user: Users = Depends(get_current_user),
) -> JSONResponse | dict[str, bool | list[Any]] | Any:
    """
    Получение информации о профиле текущего пользователя.

    Этот эндпоинт позволяет пользователю получить информацию о своем профиле,
    включая данные о подписках и подписчиках.

    :param current_user: Пользователь, полученный из зависимости `get_current_user`,
                         который извлекает текущего пользователя из состояния запроса.
                         Если пользователь не аутентифицирован, возвращается ошибка 403.
    :return:
        - result (bool): Указывает на успешность операции.
        - user (UserOut): Объект с информацией о пользователе.

    Примеры возможных ответов:
        - Успешный ответ:
            {
                "result": true,
                "user": {
                    "id": 1,
                    "username": "example_user",
                    "followers": [...],
                    "following": [...]
                }
            }
        - Ошибка 403:
            {
                "result": false,
                "error_type": "AccessDenied",
                "error_message": "Доступ запрещен: неверный API ключ"
            }
        - Ошибка 500:
            {
                "result": false,
                "error_type": "InternalServerError",
                "error_message": "Произошла ошибка на сервере"
            }

    Пример запроса:
        curl -i -X GET -H "Api-Key: 1wc65vc4v1fv" "http://localhost:5000/api/users/me"
    """

    return {"result": True, "user": current_user.to_json()}


@users_router.get(
    "/users/{user_id}",
    response_model=Dict[str, Union[bool, UserOut]],
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def get_user_info_by_id(
    user_id: int, session: AsyncSession = Depends(get_current_session)
) -> JSONResponse | dict[str, bool | list[Any]] | Any:
    """
    Пользователь может получить информацию о произвольном профиле по его id.

    Аргументы:
        user_id (int): Идентификатор пользователя, информацию о котором необходимо получить.
        session (AsyncSession): Асинхронная сессия SQLAlchemy.

    Возвращает:
        Статус операции и информация о пользователе в формате JSON.

    Пример запроса с использованием curl:
    ```
    curl -i -X GET -H "Api-Key: 1wc65vc4v1fv" "http://localhost:5000/api/users/<user_id>"
    ```

    :raises HTTPException:
        - 403, если пользователь не аутентифицирован.
        - 404, если пользователь с указанным id не найден.
        - 500, если произошла внутренняя ошибка сервера.
    """
    user_info_by_id = await UserDAO.find_one_or_none_by_id(
        user_id,
        session=session,
        options=[selectinload(Users.authors), selectinload(Users.followers)],
    )

    if user_info_by_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {"result": True, "user": user_info_by_id.to_json()}


@users_router.post("/add_user", status_code=201)
async def add_one_user(
    user: UserIn, session: AsyncSession = Depends(get_current_session)
) -> str:
    """
    Добавляет пользователя, возвращает его.

    Аргументы:
        user (UserIn): Данные нового пользователя.
        session (AsyncSession): Асинхронная сессия SQLAlchemy.

    Пример запроса:
    ```
    curl -X POST "http://localhost:8000/api/add_user" -H "Content-Type: application/json" -d '{"name": "Anon", "api_key": "1wc65vc4v1fv"}'
    ```

    Для запуска в docker-compose:
    ```
    curl -X POST "http://localhost:5000/api/add_user" -H "Content-Type: application/json" -d '{"name": "Dan", "api_key": "test"}'
    """

    logger.info(f"{user.model_dump()}")
    new_user = await UserDAO.create_user(session=session, **user.model_dump())

    return f"User added: {new_user}\n"


@users_router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    session: AsyncSession = Depends(get_current_session),
    current_user: Users = Depends(get_current_user),
) -> dict:
    """
    Пользователь может зафоловить другого пользователя.

    Аргументы:
        user_id (int): Пользователь, которого фолловят.
        current_user (Users): Пользователь, который фолловит.
        session (AsyncSession): Асинхронная сессия SQLAlchemy.

    Возвращает:
        Статус операции в формате JSON.

    Пример запроса с использованием curl:
    ```
    curl -X POST -H "Api-Key: 1wc65vc4v1fv" http://localhost:5000/api/users/<user_id>/follow
    ```

    :raises HTTPException:
        - 404, если указанный пользователь не найден.
        - 409, если пользователь уже подписан на данного пользователя.
    """
    # Проверяем, существует ли пользователь, на которого подписываются
    followed_user = await UserDAO.find_one_or_none_by_id(user_id, session=session)

    if not followed_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверяем, не подписан ли текущий пользователь уже на данного пользователя
    existing_follow = await FollowersDAO.find_one_or_none(
        account_id=user_id, follower_id=current_user.id, session=session
    )

    if existing_follow:
        raise HTTPException(
            status_code=409, detail="Вы уже подписаны на этого пользователя"
        )

    # Добавляем запись о подписке в таблицу followers
    await FollowersDAO.add_followers(
        session=session, account_id=user_id, follower_id=current_user.id
    )

    return {"result": True}


@users_router.delete("/users/{user_id}/follow")
async def delete_following(
    user_id: int,
    session: AsyncSession = Depends(get_current_session),
    current_user: Users = Depends(get_current_user),
) -> dict:
    """
    Пользователь может убрать подписку на другого пользователя.

    Аргументы:
        user_id (int): Идентификатор пользователя, от которого пользователь хочет отписаться.
        current_user (Users): Текущий пользователь, который отписывается.
        session (AsyncSession): Асинхронная сессия SQLAlchemy.

    Возвращает:
        Статус операции в формате JSON.

    Пример запроса с использованием curl:
    ```
    curl -i -X DELETE -H "Api-Key: 1wc65vc4v1fv" "http://localhost:5000/api/users/<user_id>/follow"
    ```

    :raises HTTPException:
        - 403, если пользователь не аутентифицирован.
        - 404, если пользователь, от которого отписываются, не найден.
        - 409, если текущий пользователь не подписан на данного пользователя.
    """
    # Проверяем, существует ли пользователь, от которого отписываются
    current_author = await UserDAO.find_one_or_none_by_id(user_id, session=session)

    if not current_author:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверяем, есть ли запись о подписке
    existing_follow = await FollowersDAO.find_one_or_none(
        account_id=user_id, follower_id=current_user.id, session=session
    )

    if not existing_follow:
        raise HTTPException(
            status_code=409, detail="Вы не подписаны на этого пользователя"
        )

    # Удаляем запись о подписке из таблицы followers
    await FollowersDAO.delete_followers(
        session=session, account_id=user_id, follower_id=current_user.id
    )

    return {"result": True}
