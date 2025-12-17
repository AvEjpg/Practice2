from fastapi import FastAPI
from backend.routers import users, requests, comments, auth as auth_router, client
from .database import Base, engine

# Создание таблиц (если их нет)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Climate Service API")

# Подключаем роутеры
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(requests.router, prefix="/requests", tags=["Requests"])
app.include_router(comments.router, prefix="/comments", tags=["Comments"])
app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(client.router, prefix="/client", tags=["Client"])

from backend.routers import qr
app.include_router(qr.router, prefix="/qr", tags=["QR"])

@app.get("/")
def root():
    return {"message": "Climate Service API", "version": "1.0.0"}
