from datetime import date

from sqlmodel import Field, SQLModel


# Fields the client sends (validated on create/update)
class UserBase(SQLModel):
    name: str
    age: int = Field(ge=0)
    dob: date
    location: str
    work: str


# DB table
class User(UserBase, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
