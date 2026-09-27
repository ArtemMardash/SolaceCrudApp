import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from user import User, UserBase
from user_service import UserService

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

service = UserService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.create_database()
    service.create_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/users", response_model=User, status_code=201)
def create_user(user: UserBase):
    return service.create(user)


@app.get("/users", response_model=list[User])
def get_users():
    return service.get_all()


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    user = service.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user: UserBase):
    updated = service.update(user_id, user)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    if not service.delete(user_id):
        raise HTTPException(status_code=404, detail="User not found")
