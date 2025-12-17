from pydantic import BaseModel
from typing import Optional
from datetime import date

# ---------- Requests ----------
class RequestBase(BaseModel):
    start_date: date
    climate_tech_type: str
    climate_tech_model: str
    problem_description: str
    request_status: str
    completion_date: Optional[date] = None
    repair_parts: Optional[str] = None
    master_id: Optional[int] = None
    client_id: int

class RequestCreate(RequestBase):
    pass

class RequestUpdate(BaseModel):
    request_status: Optional[str] = None
    completion_date: Optional[date] = None
    repair_parts: Optional[str] = None
    master_id: Optional[int] = None
    client_id: Optional[int] = None

class RequestOut(RequestBase):
    request_id: int

    class Config:
        from_attributes = True  # для Pydantic v2


# ---------- Users ----------
class UserBase(BaseModel):
    fio: str
    phone: str
    login: str
    password: str
    user_type: str

class UserCreate(UserBase):
    pass

class UserOut(BaseModel):
    user_id: int
    fio: str
    phone: str
    login: str
    user_type: str

    class Config:
        from_attributes = True


# ---------- Comments ----------
class CommentBase(BaseModel):
    message: str
    master_id: int
    request_id: int

class CommentCreate(CommentBase):
    pass

class CommentOut(CommentBase):
    comment_id: int

    class Config:
        from_attributes = True


# ---------- Auth ----------
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: Optional[int] = None  # Добавляем user_id

    class Config:
        from_attributes = True

class LoginIn(BaseModel):
    login: str
    password: str

# ---------- Client Requests ----------
class ClientRequestCreate(BaseModel):
    start_date: date
    climate_tech_type: str
    climate_tech_model: str
    problem_description: str
    # client_id не включаем - он берется из токена
    # статус устанавливается автоматически

class ClientRequestOut(BaseModel):
    request_id: int
    start_date: date
    climate_tech_type: str
    climate_tech_model: str
    problem_description: str
    request_status: str
    completion_date: Optional[date] = None
    repair_parts: Optional[str] = None
    master_id: Optional[int] = None
    client_id: int

    class Config:
        from_attributes = True


# ---------- Extra ----------
class AssignSpecialistIn(BaseModel):
    master_id: int

class ExtendDeadlineIn(BaseModel):
    new_completion_date: date
    reason: Optional[str] = None
