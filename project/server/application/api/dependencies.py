from crud import BaseDAO
from database import AsyncSessionApp
from fastapi import Header, HTTPException
from models import Users, Tweets, Media
from sqlalchemy.orm import selectinload
from sqlalchemy.testing.plugin.plugin_base import options


# Назначение текущей сессии
async def get_current_session():
    current_session = AsyncSessionApp()
    try:
        yield current_session
    finally:
        await current_session.close()


async def get_client_token(api_key: str = Header(...)):
    """
    Извлекает API ключ из заголовка и проверяет его на валидность.

    :param api_key: API ключ пользователя
    :return: API ключ, если он валиден
    """
    user = await UserDAO.find_one_or_none(api_key=api_key)
    if user is None:
        raise HTTPException(status_code=403, detail="Доступ запрещен: неверный API ключ")
    return api_key


class UserDAO(BaseDAO):
    model = Users


class TweetDAO(BaseDAO):
    model = Tweets

    @classmethod
    async def delete_tweet(cls, tweet_id: int, user_id: int):
        """
        Удаляет твит, если он принадлежит указанному пользователю.

        :param tweet_id: Идентификатор твита
        :param user_id: Идентификатор пользователя
        :return: True, если твит был удален, иначе False
        """
        async with AsyncSessionApp() as session:
            async with session.begin():
                tweet = await cls.find_one_or_none_by_id(
                    data_id=tweet_id,
                    options=[
                    selectinload(Tweets.attachments)
                ]
                )
                if tweet and tweet.author_id == user_id:
                    await session.delete(tweet)
                    return True
                return False

class MediaDAO(BaseDAO):
    model = Media
