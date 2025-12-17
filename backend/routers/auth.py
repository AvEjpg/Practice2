from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, models
from ..auth import create_access_token, verify_password, get_db, get_current_user
from ..crud import get_user_by_login

router = APIRouter()

@router.post("/login", response_model=schemas.TokenOut)
def login(form: schemas.LoginIn, db: Session = Depends(get_db)):
    user = get_user_by_login(db, form.login)
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")
    
    if not verify_password(form.password, user.password):
        raise HTTPException(status_code=400, detail="Неверный пароль")
    
    token = create_access_token({"sub": str(user.user_id), "role": user.user_type})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.user_type,
        "user_id": user.user_id
    }

@router.get("/me")
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return {
        "user_id": current_user.user_id,
        "login": current_user.login,
        "fio": current_user.fio,
        "phone": current_user.phone,
        "user_type": current_user.user_type
    }