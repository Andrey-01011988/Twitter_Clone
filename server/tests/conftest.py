import logging
import os
import random
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from application.models import BaseProj, Users
from application.api.dependencies import get_current_session
from application.main import app_proj
from tests.factories import (
    UserFactory,
    TweetFactory,
    LikeFactory,
    MediaFactory,
    FollowerFactory,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env.test'))
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    logger.error(f"Файл {dotenv_path} не найден.")

db_user = os.getenv("TEST_POSTGRES_USER")
db_password = os.getenv("TEST_POSTGRES_PASSWORD")
db_name = os.getenv("TEST_POSTGRES_DB")
# Строка подключения к тестовой базе данных через контейнер
test_database_url = f"postgresql+asyncpg://{db_user}:{db_password}@test_db:5432/{db_name}"

# Фикстуры с использованием фабрик
@pytest_asyncio.fixture()
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    logger.info("Start fixture")
    logger.info(f"{test_database_url}")
    test_engine_local = create_async_engine(test_database_url)
    logger.info("Engine created")
    test_async_session = async_sessionmaker(test_engine_local, expire_on_commit=False)
    logger.info("Session maker created")
    async with test_engine_local.begin() as conn:
        await conn.run_sync(BaseProj.metadata.drop_all)
        await conn.run_sync(BaseProj.metadata.create_all)
        logger.info("Drop old and create new tables")
    async with test_async_session() as session:
        logger.info(f"Create test session: {session}")
        users = []
        UserFactory._meta.sqlalchemy_session = session
        for i in range(3):
            if i == 0:
                user = UserFactory(api_key="test")
            else:
                user = UserFactory()
            users.append(user)
        logger.info(f"Create test users {users}")
        session.add_all(users)
        await session.commit()
        logger.info(f"Test users added {users}")

        tweets = []
        likes = []
        media = []
        followers = []

        # Создание подписок
        FollowerFactory._meta.sqlalchemy_session = session
        user_with_api_key_test = users[0]  # пользователь с api_key='test'
        if len(users) > 1:
            author = users[1]
            follower_record = FollowerFactory(
                account_id=author.id, follower_id=user_with_api_key_test.id
            )
            followers.append(follower_record)
        for author in users[1:]:
            follower = random.choice(
                [user for user in users if user != author and user.api_key != "test"]
            )
            logger.info(f"author id: {author.name, author.id}")
            logger.info(f"follower id: {follower.name, follower.id}")
            follower_record = FollowerFactory(
                account_id=author.id, follower_id=follower.id
            )
            followers.append(follower_record)
        session.add_all(followers)
        logger.info(f"Followers created {followers}")

        # Создание твитов
        TweetFactory._meta.sqlalchemy_session = session
        for user in users:
            for _ in range(2):
                tweet = TweetFactory(author_id=user.id)
                tweets.append(tweet)
        logger.info(
            f"Tweets created: {[(tweet.text, tweet.author_id) for tweet in tweets]}"
        )
        session.add_all(tweets)
        await session.commit()
        logger.info(
            f"Followers added {[(i.account_id, i.follower_id) for i in followers]}"
        )
        logger.info(f"Tweets added: {[tweet.id for tweet in tweets]}")

        # Создание лайков
        LikeFactory._meta.sqlalchemy_session = session
        for tweet in tweets:
            # Обязательное добавление лайка
            if tweet.id == 3:
                like = LikeFactory(tweet_id=tweet.id, user_id=users[0].id)
                likes.append(like)
            elif random.choice([True, False]):
                like = LikeFactory(
                    tweet_id=tweet.id,
                    user_id=random.choice(
                        [user for user in users if user.api_key != "test"]
                    ).id,
                )
                likes.append(like)
        logger.info(f"Likes created: {likes}")
        session.add_all(likes)

        # Создание медиа
        MediaFactory._meta.sqlalchemy_session = session
        for tweet in tweets:
            # Обязательное добавление медиа
            if tweet.id == 1:
                media_item = MediaFactory(tweet_id=tweet.id)
                media.append(media_item)
            elif random.choice([True, False]):
                media_item = MediaFactory(tweet_id=tweet.id)
                media.append(media_item)
        logger.info(
            f"Media created: {[(med.file_name, med.tweet_id) for med in media]}"
        )
        session.add_all(media)

        await session.commit()
        logger.info(f"Likes added: {[like.id for like in likes]}")
        logger.info(f"Media added: {[med.id for med in media]}")
        logger.info("Likes & media added")

        yield session
        logger.info(f"Preparation for closing the session {session}")
        await session.close()
        logger.info("Session closed")
    async with test_engine_local.begin() as conn:
        await conn.run_sync(BaseProj.metadata.drop_all)
        logger.info("Tables dropped")


@pytest.fixture()
def test_app(test_db_session: AsyncSession) -> FastAPI:
    app_proj.dependency_overrides[get_current_session] = lambda: test_db_session
    logger.info("Override dependency")
    return app_proj


@pytest_asyncio.fixture()
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test_server:5000",  # для контейнера
    ) as client:
        logger.info("Create test client")
        yield client


# (ubuntuenv) uservm@uservm-VirtualBox:~/PycharmProjects/python_advanced_diploma/project/server$ docker exec -it project_test_server_1 /bin/sh
# pytest -v tests/ --log-cli-level=INFO
