import logging
import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select, text

from user import User, UserBase

load_dotenv()

logger = logging.getLogger(__name__)


def db_url(db_name: str) -> str:
    return (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{db_name}"
    )


class UserService:
    def __init__(self):
        self.db_name = os.environ["DB_NAME"]
        self.engine = create_engine(db_url(self.db_name))

    def create_database(self):
        # CREATE DATABASE can't run inside a transaction, so connect to the
        # default "postgres" database in autocommit mode
        admin_engine = create_engine(db_url("postgres"), isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": self.db_name}
            ).scalar()
            if exists:
                logger.info("Database '%s' already exists", self.db_name)
            else:
                conn.execute(text(f'CREATE DATABASE "{self.db_name}"'))
                logger.info("Created database '%s'", self.db_name)
        admin_engine.dispose()

    def create_tables(self):
        SQLModel.metadata.create_all(self.engine)
        logger.info("Tables ready")

    def create(self, data: UserBase) -> User:
        user = User.model_validate(data)
        with Session(self.engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("Created user id=%s", user.id)
            return user

    def get_all(self) -> list[User]:
        with Session(self.engine) as session:
            users = list(session.exec(select(User)).all())
            logger.debug("Fetched %d users", len(users))
            return users

    def get(self, user_id: int) -> User | None:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if user is None:
                logger.warning("User id=%s not found", user_id)
            return user

    def update(self, user_id: int, data: UserBase) -> User | None:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if user is None:
                logger.warning("Update failed: user id=%s not found", user_id)
                return None
            user.sqlmodel_update(data.model_dump())
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("Updated user id=%s", user_id)
            return user

    def delete(self, user_id: int) -> bool:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if user is None:
                logger.warning("Delete failed: user id=%s not found", user_id)
                return False
            session.delete(user)
            session.commit()
            logger.info("Deleted user id=%s", user_id)
            return True
