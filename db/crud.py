from typing import Optional, List

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, joinedload, selectinload

from .models import User, Post, Tag


# --- Users ---

def create_user(session: Session, username: str, email: str) -> User:
    user = User(username=username, email=email)
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    return session.get(User, user_id)


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    return session.scalars(select(User).where(User.username == username)).first()


def update_user_email(session: Session, user_id: int, new_email: str) -> Optional[User]:
    # ORM-style: загружаем объект → меняем атрибут → SQLAlchemy сам сгенерирует UPDATE
    user = session.get(User, user_id)
    if user is None:
        return None
    user.email = new_email
    session.flush()
    return user


def deactivate_user(session: Session, user_id: int) -> bool:
    # Core-style: UPDATE без загрузки объекта — эффективно для массовых операций
    result = session.execute(
        update(User).where(User.id == user_id).values(is_active=False)
    )
    return result.rowcount > 0


def delete_user(session: Session, user_id: int) -> bool:
    user = session.get(User, user_id)
    if user is None:
        return False
    session.delete(user)  # cascade удалит все посты пользователя
    session.flush()
    return True


# --- Posts ---

def create_post(
    session: Session,
    user_id: int,
    title: str,
    body: str = "",
    tag_names: Optional[List[str]] = None,
) -> Optional[Post]:
    if session.get(User, user_id) is None:
        return None
    post = Post(title=title, body=body, user_id=user_id)
    session.add(post)
    if tag_names:
        for name in tag_names:
            post.tags.append(_get_or_create_tag(session, name))
    session.flush()
    session.refresh(post)
    return post


def get_post_with_relations(session: Session, post_id: int) -> Optional[Post]:
    # joinedload  — LEFT JOIN для *-to-one (Post → User)
    # selectinload — отдельный SELECT IN для *-to-many (Post → Tags)
    stmt = (
        select(Post)
        .where(Post.id == post_id)
        .options(joinedload(Post.author), selectinload(Post.tags))
    )
    return session.scalars(stmt).first()


def get_posts_by_user(session: Session, user_id: int) -> List[Post]:
    stmt = (
        select(Post)
        .where(Post.user_id == user_id)
        .options(selectinload(Post.tags))
        .order_by(Post.created_at.desc())
    )
    return list(session.scalars(stmt))


def get_posts_by_tag(session: Session, tag_name: str) -> List[Post]:
    # Post.tags.any(...) → EXISTS subquery
    stmt = (
        select(Post)
        .where(Post.tags.any(Tag.name == tag_name))
        .options(joinedload(Post.author), selectinload(Post.tags))
    )
    return list(session.scalars(stmt).unique())


def publish_post(session: Session, post_id: int) -> Optional[Post]:
    post = session.get(Post, post_id)
    if post is None:
        return None
    post.published = True
    session.flush()
    return post


def delete_post(session: Session, post_id: int) -> bool:
    post = session.get(Post, post_id)
    if post is None:
        return False
    session.delete(post)
    session.flush()
    return True


# --- Aggregations ---

def count_posts_per_user(session: Session) -> List[dict]:
    stmt = (
        select(User.username, func.count(Post.id).label("post_count"))
        .join(Post, Post.user_id == User.id, isouter=True)  # LEFT JOIN
        .group_by(User.id, User.username)
        .order_by(func.count(Post.id).desc())
    )
    return [{"username": r.username, "post_count": r.post_count} for r in session.execute(stmt)]


# --- Internal ---

def _get_or_create_tag(session: Session, name: str) -> Tag:
    tag = session.scalars(select(Tag).where(Tag.name == name)).first()
    if tag is None:
        tag = Tag(name=name)
        session.add(tag)
        session.flush()
    return tag
