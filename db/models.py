from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Table, Column, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# Association table для many-to-many: Post <-> Tag
post_tags = Table(
    "post_tags", Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # one-to-many: один User → много Post
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="author", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[Optional[str]] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # many-to-one: много Post → один User
    author: Mapped["User"] = relationship("User", back_populates="posts")

    # many-to-many: Post <-> Tag через post_tags
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=post_tags, back_populates="posts")

    def __repr__(self):
        return f"<Post id={self.id} title={self.title!r}>"


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    posts: Mapped[List["Post"]] = relationship("Post", secondary=post_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag id={self.id} name={self.name!r}>"
