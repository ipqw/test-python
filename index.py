from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from db.database import create_tables, get_session
from db import crud

create_tables()


# Каждый @tool — это операция с БД, которую агент может вызвать самостоятельно.
# LangChain читает docstring как описание инструмента для LLM.

@tool
def add_user(username: str, email: str) -> str:
    """Add a new user to the database."""
    with get_session() as session:
        user = crud.create_user(session, username, email)
        return repr(user)


@tool
def find_user(username: str) -> str:
    """Find a user by username."""
    with get_session() as session:
        user = crud.get_user_by_username(session, username)
        return repr(user) if user else "User not found."


@tool
def add_post(user_id: int, title: str, body: str, tags: list[str] = []) -> str:
    """Create a post for a user. Optionally attach tags."""
    with get_session() as session:
        post = crud.create_post(session, user_id, title, body, tags)
        return repr(post) if post else "User not found."


@tool
def get_user_posts(user_id: int) -> str:
    """Get all posts by a user."""
    with get_session() as session:
        posts = crud.get_posts_by_user(session, user_id)
        return "\n".join(repr(p) for p in posts) or "No posts."


@tool
def find_posts_by_tag(tag: str) -> str:
    """Find all posts with a given tag."""
    with get_session() as session:
        posts = crud.get_posts_by_tag(session, tag)
        return "\n".join(repr(p) for p in posts) or "No posts."


@tool
def post_stats() -> str:
    """Show post count per user."""
    with get_session() as session:
        stats = crud.count_posts_per_user(session)
        return "\n".join(f"{r['username']}: {r['post_count']} posts" for r in stats)


tools = [add_user, find_user, add_post, get_user_posts, find_posts_by_tag, post_stats]

model = ChatOpenAI(model="gpt-4o-mini")
agent = create_agent(
    model,
    tools,
    system_prompt="You are a database assistant. Use tools to manage users and posts.",
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": (
            "Create user alice (alice@mail.com) and bob (bob@mail.com). "
            "Add two posts for alice: one about SQLAlchemy with tags 'python' and 'orm', "
            "one about PostgreSQL with tag 'database'. "
            "Then show all posts with tag 'python' and the overall stats."
        ),
    }]
})

for message in result["messages"]:
    print(message)
