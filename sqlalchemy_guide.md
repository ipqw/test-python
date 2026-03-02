# SQLAlchemy — полный гайд для новичков

## Содержание
1. [Что такое ORM и зачем он нужен](#1-что-такое-orm-и-зачем-он-нужен)
2. [Установка и подключение](#2-установка-и-подключение)
3. [Engine — соединение с базой](#3-engine--соединение-с-базой)
4. [Модели — описание таблиц](#4-модели--описание-таблиц)
5. [Типы колонок](#5-типы-колонок)
6. [Session — как работать с данными](#6-session--как-работать-с-данными)
7. [CREATE — добавление записей](#7-create--добавление-записей)
8. [READ — чтение данных](#8-read--чтение-данных)
9. [UPDATE — изменение записей](#9-update--изменение-записей)
10. [DELETE — удаление записей](#10-delete--удаление-записей)
11. [Связи между таблицами](#11-связи-между-таблицами)
12. [Проблема N+1 и её решение](#12-проблема-n1-и-её-решение)
13. [Агрегации и группировка](#13-агрегации-и-группировка)
14. [Транзакции](#14-транзакции)
15. [Частые ошибки](#15-частые-ошибки)

---

## 1. Что такое ORM и зачем он нужен

**ORM** (Object-Relational Mapping) — прослойка, которая позволяет работать с базой данных через Python-объекты, а не через сырой SQL.

**Без ORM:**
```python
cursor.execute("SELECT * FROM users WHERE id = %s", (1,))
row = cursor.fetchone()
# row — просто кортеж: (1, 'alice', 'alice@mail.com')
```

**С ORM:**
```python
user = session.get(User, 1)
print(user.username)  # 'alice' — обычный атрибут объекта
```

ORM автоматически:
- генерирует SQL из Python-кода
- превращает строки таблицы в объекты
- отслеживает изменения объектов
- управляет транзакциями

SQLAlchemy — самый мощный и популярный ORM для Python. В этом гайде используется **SQLAlchemy 2.0** (современный синтаксис).

---

## 2. Установка и подключение

```bash
pip install sqlalchemy psycopg2-binary
```

- `sqlalchemy` — сам ORM
- `psycopg2-binary` — драйвер для PostgreSQL (адаптер между Python и PostgreSQL)

---

## 3. Engine — соединение с базой

**Engine** — точка входа в базу данных. Он знает, как подключаться к БД и управляет пулом соединений.

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg2://user:password@localhost:5432/mydb",
    echo=True,  # выводить SQL в консоль — удобно при обучении
)
```

**Строка подключения** разбирается так:

```
postgresql+psycopg2  ://  user  :  password  @  localhost  :  5432  /  mydb
│           │              │        │             │           │        │
диалект  драйвер         логин   пароль         хост        порт    имя БД
```

Engine **не открывает соединение** при создании — только при первом запросе.

---

## 4. Модели — описание таблиц

Модель — это Python-класс, который описывает таблицу в БД. Каждый атрибут — колонка.

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"  # имя таблицы в PostgreSQL

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100))
```

**Ключевые понятия:**

`Base` — общий родитель всех моделей. Хранит информацию обо всех таблицах.

`Mapped[int]` — аннотация типа, говорит SQLAlchemy что это колонка типа int. Используется только в моделях.

`mapped_column()` — настройка колонки: ограничения, дефолты, индексы.

**Создать таблицы в БД:**
```python
Base.metadata.create_all(engine)
# Выполняет CREATE TABLE IF NOT EXISTS для каждой модели
```

---

## 5. Типы колонок

```python
from sqlalchemy import String, Integer, Text, Boolean, DateTime, Float, Numeric
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime
from typing import Optional
from sqlalchemy import func

class Example(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    # primary_key=True — первичный ключ, автоинкремент в PostgreSQL

    name: Mapped[str] = mapped_column(String(100))
    # String(100) — VARCHAR(100), ограничение длины

    bio: Mapped[Optional[str]] = mapped_column(Text)
    # Optional[str] — колонка может быть NULL
    # Text — неограниченная длина строки

    age: Mapped[int] = mapped_column(default=18)
    # default=18 — значение по умолчанию на уровне Python

    score: Mapped[float] = mapped_column(Float)
    # Float — число с плавающей точкой

    price: Mapped[float] = mapped_column(Numeric(10, 2))
    # Numeric(10, 2) — точное число: 10 цифр, 2 после запятой (для денег)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
        # server_default — значение задаёт PostgreSQL, не Python
        # func.now() → SQL: DEFAULT NOW()
    )
```

**Разница `default` vs `server_default`:**
- `default=value` — Python подставляет значение перед отправкой запроса
- `server_default=func.now()` — PostgreSQL сам вставляет значение при INSERT

Для временных меток используй `server_default` — тогда время всегда точное (время сервера БД).

---

## 6. Session — как работать с данными

**Session** — основной инструмент для работы с данными. Это "единица работы":

- хранит все объекты, которые ты загрузил или создал
- отслеживает изменения в объектах
- отправляет SQL только при `flush()` или `commit()`
- при `commit()` фиксирует транзакцию

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

# Создать сессию
session = SessionLocal()

# ... работа с данными ...

session.commit()   # зафиксировать изменения
session.close()    # закрыть сессию
```

**Лучший способ — через контекстный менеджер:**
```python
from contextlib import contextmanager

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()  # откат при ошибке
        raise
    finally:
        session.close()

# Использование:
with get_session() as session:
    user = session.get(User, 1)
# session автоматически закрылась, изменения зафиксированы
```

**Жизненный цикл объекта в сессии:**

```
Создан в Python → pending
      ↓ flush/commit
  Сохранён в БД → persistent  ←→  Изменён → dirty (будет UPDATE при flush)
      ↓ session.delete()
    Помечен      → deleted    →  Удалён из БД при flush
      ↓ session.close()
   Отсоединён   → detached   (объект есть, но сессия закрыта)
```

---

## 7. CREATE — добавление записей

```python
with get_session() as session:
    # Создать объект и добавить в сессию
    user = User(username="alice", email="alice@mail.com")
    session.add(user)

    # До commit() запись ещё не в БД, но SQLAlchemy знает о ней
    print(user.id)  # None — id ещё не присвоен

    session.flush()  # отправляет INSERT, но транзакция ещё открыта
    print(user.id)  # 1 — PostgreSQL присвоил id

    # При выходе из блока with — автоматический commit
```

**Добавить несколько записей сразу:**
```python
with get_session() as session:
    users = [
        User(username="alice", email="alice@mail.com"),
        User(username="bob",   email="bob@mail.com"),
        User(username="carol", email="carol@mail.com"),
    ]
    session.add_all(users)
    # Один INSERT ... VALUES (...), (...), (...)
```

---

## 8. READ — чтение данных

### По первичному ключу

```python
with get_session() as session:
    user = session.get(User, 1)
    # Возвращает объект User или None
    # Сначала проверяет кэш сессии, потом идёт в БД
```

### Простой SELECT

```python
from sqlalchemy import select

with get_session() as session:
    # select(Model) — эквивалент SELECT * FROM users
    stmt = select(User)
    users = session.scalars(stmt).all()
    # scalars() — извлекает первую колонку из результата (наш объект)
    # .all() — возвращает список
```

### WHERE — фильтрация

```python
with get_session() as session:
    stmt = select(User).where(User.username == "alice")
    user = session.scalars(stmt).first()
    # .first() — первый результат или None
```

**Операторы фильтрации:**

```python
# Равенство / неравенство
.where(User.age == 25)
.where(User.age != 25)

# Сравнение
.where(User.age > 18)
.where(User.age >= 18)
.where(User.age < 65)

# NULL
.where(User.bio == None)   # IS NULL
.where(User.bio != None)   # IS NOT NULL

# LIKE / ILIKE (без учёта регистра)
.where(User.username.like("ali%"))    # начинается с "ali"
.where(User.username.ilike("%ALICE%"))

# IN
.where(User.id.in_([1, 2, 3]))

# AND / OR
from sqlalchemy import and_, or_
.where(and_(User.age > 18, User.is_active == True))
.where(or_(User.username == "alice", User.username == "bob"))

# Краткая форма AND (перечисление через запятую):
.where(User.age > 18, User.is_active == True)
```

### ORDER BY, LIMIT, OFFSET

```python
with get_session() as session:
    stmt = (
        select(User)
        .order_by(User.username)        # сортировка по возрастанию
        .order_by(User.created_at.desc())  # по убыванию
        .limit(10)                      # первые 10 записей
        .offset(20)                     # пропустить первые 20
    )
    users = session.scalars(stmt).all()
```

### Выбрать конкретные колонки

```python
with get_session() as session:
    stmt = select(User.username, User.email)
    rows = session.execute(stmt).all()
    # execute() вместо scalars() — возвращает кортежи (username, email)
    for row in rows:
        print(row.username, row.email)
```

---

## 9. UPDATE — изменение записей

### ORM-стиль (через объект)

```python
with get_session() as session:
    user = session.get(User, 1)
    user.email = "new@mail.com"  # SQLAlchemy видит изменение
    # При commit() автоматически выполнится UPDATE users SET email=... WHERE id=1
```

### Core-стиль (bulk update, без загрузки объектов)

```python
from sqlalchemy import update

with get_session() as session:
    stmt = (
        update(User)
        .where(User.is_active == False)
        .values(email="deleted@mail.com")
    )
    result = session.execute(stmt)
    print(result.rowcount)  # сколько строк изменено
```

**Когда что использовать:**
- ORM-стиль — когда объект уже загружен, нужно обновить пару полей
- Core-стиль — когда нужно обновить много строк без загрузки в память

---

## 10. DELETE — удаление записей

### ORM-стиль

```python
with get_session() as session:
    user = session.get(User, 1)
    session.delete(user)
    # При commit() выполнится DELETE FROM users WHERE id=1
```

### Core-стиль (bulk delete)

```python
from sqlalchemy import delete

with get_session() as session:
    stmt = delete(User).where(User.is_active == False)
    result = session.execute(stmt)
    print(f"Удалено: {result.rowcount}")
```

---

## 11. Связи между таблицами

### Один ко многим (one-to-many)

Один пользователь — много постов.

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from typing import List

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

    # "у пользователя много постов"
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # ForeignKey("users.id") — ссылка на id в таблице users

    # "у поста один автор"
    author: Mapped["User"] = relationship("User", back_populates="posts")
```

**`back_populates`** — делает связь двусторонней:
```python
user.posts   # список постов пользователя
post.author  # пользователь, написавший пост
```

**Cascade — что происходит с постами при удалении пользователя:**
```python
posts: Mapped[List["Post"]] = relationship(
    "Post",
    back_populates="author",
    cascade="all, delete-orphan"
    # При удалении User — удалятся все его Post
)
```

### Многие ко многим (many-to-many)

Один пост — много тегов. Один тег — много постов.

```python
from sqlalchemy import Table, Column

# Промежуточная таблица — нет Python-класса, только таблица
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))

    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=post_tags,   # промежуточная таблица
        back_populates="posts",
    )

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    posts: Mapped[List["Post"]] = relationship(
        "Post",
        secondary=post_tags,
        back_populates="tags",
    )
```

**Использование:**
```python
with get_session() as session:
    post = session.get(Post, 1)
    tag = Tag(name="python")
    post.tags.append(tag)
    # SQLAlchemy сам добавит строку в post_tags
```

---

## 12. Проблема N+1 и её решение

**Проблема N+1** — классическая ошибка при работе с ORM.

```python
# ПЛОХО: N+1 запросов
with get_session() as session:
    posts = session.scalars(select(Post)).all()  # 1 запрос
    for post in posts:
        print(post.author.username)  # N запросов (по одному на каждый пост!)
```

При доступе к `post.author` SQLAlchemy "лениво" загружает автора — выполняет отдельный SELECT. Если 100 постов — 100 дополнительных запросов.

**Решение — eager loading (жадная загрузка):**

```python
from sqlalchemy.orm import joinedload, selectinload

# joinedload — один запрос с JOIN
# Хорошо для связей *-to-one (Post → User)
stmt = select(Post).options(joinedload(Post.author))
posts = session.scalars(stmt).unique().all()
# .unique() нужен при joinedload, чтобы убрать дубликаты из JOIN

# selectinload — отдельный SELECT ... WHERE id IN (...)
# Хорошо для связей *-to-many (User → Posts, Post → Tags)
stmt = select(Post).options(selectinload(Post.tags))
posts = session.scalars(stmt).all()
```

**Когда что использовать:**
- `joinedload` → для связей "к одному" (ForeignKey в текущей модели)
- `selectinload` → для связей "ко многим" (список объектов)

```python
# Несколько уровней загрузки сразу:
stmt = (
    select(Post)
    .options(
        joinedload(Post.author),
        selectinload(Post.tags),
    )
)
```

---

## 13. Агрегации и группировка

```python
from sqlalchemy import func, select

with get_session() as session:
    # COUNT
    total = session.scalar(select(func.count(User.id)))
    print(f"Пользователей: {total}")

    # MAX, MIN, AVG, SUM
    stmt = select(func.max(User.id), func.min(User.id))
    row = session.execute(stmt).one()
    print(row.max_1, row.min_1)

    # GROUP BY — количество постов у каждого пользователя
    stmt = (
        select(
            User.username,
            func.count(Post.id).label("post_count"),
        )
        .join(Post, Post.user_id == User.id, isouter=True)
        # isouter=True — LEFT JOIN (включая пользователей без постов)
        .group_by(User.id, User.username)
        .order_by(func.count(Post.id).desc())
    )
    rows = session.execute(stmt).all()
    for row in rows:
        print(f"{row.username}: {row.post_count} постов")

    # HAVING — фильтр после группировки
    stmt = (
        select(User.username, func.count(Post.id).label("cnt"))
        .join(Post, Post.user_id == User.id)
        .group_by(User.id, User.username)
        .having(func.count(Post.id) > 5)  # только те, у кого > 5 постов
    )
```

---

## 14. Транзакции

Транзакция — группа операций, которые либо все выполняются, либо все откатываются.

```python
with get_session() as session:
    try:
        user = User(username="alice", email="alice@mail.com")
        session.add(user)
        session.flush()

        post = Post(title="Первый пост", user_id=user.id)
        session.add(post)

        # Всё ок — commit зафиксирует обе операции
    except Exception:
        # При ошибке — rollback откатит всё
        # get_session() делает это автоматически
        raise
```

**Вложенные транзакции (savepoint)** — откат части операций:
```python
with get_session() as session:
    user = User(username="alice", email="alice@mail.com")
    session.add(user)

    # Savepoint — точка, к которой можно откатиться
    with session.begin_nested():
        try:
            bad_post = Post(title="", user_id=user.id)
            session.add(bad_post)
            session.flush()
        except Exception:
            pass  # откатится только этот блок, user останется

    # user сохранится, bad_post — нет
```

---

## 15. Частые ошибки

### 1. Использование объекта после закрытия сессии

```python
# ОШИБКА: DetachedInstanceError
with get_session() as session:
    user = session.get(User, 1)
# сессия закрыта

print(user.posts)  # ошибка! сессия закрыта, нельзя загрузить posts
```

**Решение:** загружай всё нужное внутри сессии через `selectinload` / `joinedload`.

---

### 2. Забыть commit

```python
session = SessionLocal()
user = User(username="alice", email="alice@mail.com")
session.add(user)
session.close()  # нет commit — данные не сохранились!
```

**Решение:** всегда используй контекстный менеджер `get_session()`.

---

### 3. Изменять объект после detach

```python
with get_session() as session:
    user = session.get(User, 1)

user.email = "new@mail.com"  # изменение есть, но сессии нет
# commit некому вызывать — изменение потеряется
```

---

### 4. N+1 запросы (см. раздел 12)

```python
# Всегда думай: буду ли я обращаться к связанным объектам?
# Если да — используй joinedload / selectinload
```

---

### 5. Неверный тип в ForeignKey

```python
# Тип колонки и тип ForeignKey должны совпадать
class Post(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    #                                                ^^^^^^^^
    #                              имя таблицы, не имя класса
```

---

## Итоговая шпаргалка

```python
# Подключение
engine = create_engine("postgresql+psycopg2://user:pass@host/db")
SessionLocal = sessionmaker(bind=engine)

# Модель
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

# Создать таблицы
Base.metadata.create_all(engine)

# CRUD
with get_session() as session:
    # Create
    session.add(User(name="alice"))

    # Read
    user = session.get(User, 1)
    users = session.scalars(select(User).where(User.name == "alice")).all()

    # Update
    user.name = "bob"

    # Delete
    session.delete(user)
```
