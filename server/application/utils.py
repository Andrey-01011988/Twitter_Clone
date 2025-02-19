import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from application.api.dependencies import UserDAO, TweetDAO
from application.models import Users


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def add_test_information(session: AsyncSession):
    logger.info("Создание новой сессии для добавления тестового пользователя %s", session)
    try:
        test_user = await  UserDAO.find_one_or_none(
            session=session,
            options=[selectinload(Users.followers)],
            api_key="test"
        )

        if test_user is None:
            first_user = await UserDAO.create_user(session=session, name="Dan", api_key="test")
            second_user = await UserDAO.create_user(session=session, name="Mike", api_key="good")
            logger.info("Тестовые пользователи успешно добавлены: %s, %s", first_user, second_user)
            test_tweet = await TweetDAO.add(session=session, text="Hello!", author_id=second_user.id)
            logger.info(
                "Тестовый твит добавлен: %s, id пользователя: %s", test_tweet.text, test_tweet.author_id
            )
    except Exception as e:
        logger.error("Ошибка при добавлении тестового пользователя: %s", e)
    finally:
        logger.info("Закрытие сессии %s", session)
        await session.close()
        logger.info("Сессия закрыта")
