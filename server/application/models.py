from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import Integer, ForeignKey, String, DateTime, func, LargeBinary
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BaseProj(AsyncAttrs, DeclarativeBase):
    pass


class Followers(BaseProj):
    """
    Эта модель представляет собой ассоциативную таблицу, которая связывает пользователей с их подписками.
    author_id и follower_id являются внешними ключами, указывающими на идентификаторы пользователей в таблице users.
    Оба поля определены как первичные ключи, что позволяет избежать дублирования записей о подписках.
    """

    __tablename__ = "followers"

    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True
    )
    follower_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True
    )


class Users(BaseProj):
    """
    Модель Users хранит информацию о каждом пользователе.
    Поля:
    id: уникальный идентификатор пользователя.
    name: имя пользователя.
    api_key: уникальный ключ для аутентификации пользователя.
    Связь tweets указывает на все твиты, созданные пользователем.
    Связь followers реализует отношения "многие ко многим" между пользователями:
        secondary=Followers.__tablename__: указывает на ассоциативную таблицу followers.
        primaryjoin и secondaryjoin: определяют условия соединения таблиц для получения подписчиков и подписанных пользователей.
    def __repr__(self): Возвращает строковое представление пользователя.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(String, unique=True, index=True)

    tweets: Mapped[List["Tweets"]] = relationship(back_populates="author")

    followers = relationship(
        "Users",  # Указывает, что это отношение связано с моделью Users.
        secondary=Followers.__tablename__,  # Определяет условие соединения для получения подписчиков
        # (т.е. пользователей, которые следуют за текущим пользователем).
        primaryjoin=id == Followers.account_id,
        secondaryjoin=id
        == Followers.follower_id,  # Определяет условие соединения для получения пользователей,
        # на которых подписан текущий пользователь.
        backref="authors",  # Создает обратное отношение, позволяющее получить всех пользователей,
        # на которых подписан текущий пользователь через атрибут 'following'.
    )

    def __repr__(self):
        return f"Пользователь: {self.name}, id: {self.id}"

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "followers": (
                [
                    {"id": follower.id, "name": follower.name}
                    for follower in self.followers
                ]
                if self.followers
                else []
            ),
            "following": (
                [{"id": author.id, "name": author.name} for author in self.authors]
                if self.authors
                else []
            ),
        }


class Tweets(BaseProj):
    """
    Модель Tweets хранит информацию о каждом твите.
    Поля:
    id: уникальный идентификатор твита.
    text: текст твита.
    timestamp: время создания твита (по умолчанию текущее время).
    author_id: идентификатор автора твита (внешний ключ).
    Связи:
    author: связь с моделью пользователей.
    likes: связь с моделью лайков.
    attachments: связь с моделью медиафайлов.
    def __repr__(self): Возвращает строковое представление твита.
    """

    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    author: Mapped["Users"] = relationship("Users", back_populates="tweets")
    likes: Mapped[List["Like"]] = relationship(
        "Like", back_populates="tweet", cascade="all, delete-orphan"
    )
    # Изменяем строку media на attachments
    attachments: Mapped[List["Media"]] = relationship(
        "Media", back_populates="tweet", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"Твит: {self.text}, создан: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, Пользователем: {self.author.name}"

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.text,
            "timestamp": self.timestamp.isoformat(),  # Перевод значения datetime в строковое
            "author": {
                "id": self.author.id,
                "name": self.author.name,
            },
            "attachments": (
                [f"/api/media/{i_attachment.id}" for i_attachment in self.attachments]
                if self.attachments
                else []
            ),
            "likes": (
                [
                    {"user_id": like.user_id, "name": like.user.name}
                    for like in self.likes
                ]
                if self.likes
                else []
            ),
        }


class Like(BaseProj):
    """
    Модель Like связывает пользователей с твитами, которые они лайкают.
    Поля:
    id: уникальный идентификатор лайка.
    tweet_id: идентификатор твита (внешний ключ).
    user_id: идентификатор пользователя (внешний ключ).
    """

    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tweet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    tweet: Mapped["Tweets"] = relationship("Tweets", back_populates="likes")
    user: Mapped["Users"] = relationship("Users")


class Media(BaseProj):
    """
    Модель представления медиа-объектов, связанных с твитами.

    Эта модель используется для хранения информации о медиафайлах,
    которые могут быть прикреплены к твитам. Каждый медиа-объект
    имеет уникальный идентификатор и может содержать бинарные данные
    файла, его имя и ссылку на соответствующий твит.

    Атрибуты:
        id (int): Уникальный идентификатор медиа-объекта.
                  Является первичным ключом таблицы.

        file_body (bytes): Бинарные данные файла. Используется для
                           хранения содержимого медиафайла (например, изображений, видео).

        file_name (str): Имя файла, которое будет использоваться для
                         идентификации медиа-объекта.

        tweet_id (int): Идентификатор твита, к которому прикреплен
                         данный медиа-объект. Является внешним ключом на таблицу "tweets".

        tweet (Tweets): Отношение к модели `Tweets`. Позволяет получить
                        доступ к твиту, к которому прикреплен данный медиа-объект.
    """

    __tablename__ = "media"  # Убедитесь, что имя таблицы соответствует вашему проекту

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_body: Mapped[bytes] = mapped_column(
        LargeBinary
    )  # Хранит бинарные данные файла
    file_name: Mapped[str] = mapped_column(String)  # Имя файла
    tweet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=True
    )  # Внешний ключ на твиты

    tweet: Mapped["Tweets"] = relationship("Tweets", back_populates="attachments")
