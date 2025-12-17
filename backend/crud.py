from sqlalchemy.orm import Session
from sqlalchemy import text
from . import models, schemas

def get_requests(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Request).offset(skip).limit(limit).all()

def get_request(db: Session, request_id: int):
    return db.query(models.Request).filter(models.Request.request_id == request_id).first()

def create_request(db: Session, request: schemas.RequestCreate):
    try:
        db_request = models.Request(**request.dict())
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        return db_request
    except Exception as e:
        db.rollback()
        
        # Если ошибка связана с дублированием ID
        if "requests_pkey" in str(e) or "duplicate key" in str(e).lower():
            try:
                # Исправляем sequence вручную
                fix_sequence_query = """
                    SELECT setval('climate_service.requests_request_id_seq', 
                    (SELECT COALESCE(MAX(request_id), 0) FROM climate_service.requests) + 1, false);
                """
                db.execute(text(fix_sequence_query))
                db.commit()
                
                # Пробуем снова создать заявку
                db_request = models.Request(**request.dict())
                db.add(db_request)
                db.commit()
                db.refresh(db_request)
                return db_request
                
            except Exception as seq_error:
                db.rollback()
                raise Exception(f"Ошибка при создании заявки: {str(seq_error)}")
        else:
            raise e

def update_request(db: Session, request_id: int, request_update: schemas.RequestUpdate):
    db_request = get_request(db, request_id)
    if not db_request:
        return None
    for key, value in request_update.dict(exclude_unset=True).items():
        setattr(db_request, key, value)
    db.commit()
    db.refresh(db_request)
    return db_request

def delete_request(db: Session, request_id: int):
    db_request = get_request(db, request_id)
    if not db_request:
        return None
    db.delete(db_request)
    db.commit()
    return db_request

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    try:
        db_user = models.User(
            fio=user.fio, phone=user.phone, login=user.login,
            password=hash_password(user.password),
            user_type=user.user_type
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        
        # Если ошибка связана с дублированием ID
        if "users_pkey" in str(e) or "duplicate key" in str(e).lower():
            try:
                # Исправляем sequence вручную
                fix_sequence_query = """
                    SELECT setval('climate_service.users_user_id_seq', 
                    (SELECT COALESCE(MAX(user_id), 0) FROM climate_service.users) + 1, false);
                """
                db.execute(text(fix_sequence_query))
                db.commit()
                
                # Пробуем снова
                db_user = models.User(
                    fio=user.fio, phone=user.phone, login=user.login,
                    password=hash_password(user.password),
                    user_type=user.user_type
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                return db_user
                
            except Exception as seq_error:
                db.rollback()
                raise Exception(f"Ошибка при создании пользователя: {str(seq_error)}")
        else:
            raise e

def delete_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    db.delete(db_user)
    db.commit()
    return db_user

def get_comments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Comment).offset(skip).limit(limit).all()

def get_comment(db: Session, comment_id: int):
    return db.query(models.Comment).filter(models.Comment.comment_id == comment_id).first()

def create_comment(db: Session, comment: schemas.CommentCreate):
    try:
        db_comment = models.Comment(**comment.dict())
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment
    except Exception as e:
        db.rollback()
        
        # Если ошибка связана с дублированием ID
        if "comments_pkey" in str(e) or "duplicate key" in str(e).lower():
            try:
                # Исправляем sequence вручную
                fix_sequence_query = """
                    SELECT setval('climate_service.comments_comment_id_seq', 
                    (SELECT COALESCE(MAX(comment_id), 0) FROM climate_service.comments) + 1, false);
                """
                db.execute(text(fix_sequence_query))
                db.commit()
                
                # Пробуем снова
                db_comment = models.Comment(**comment.dict())
                db.add(db_comment)
                db.commit()
                db.refresh(db_comment)
                return db_comment
                
            except Exception as seq_error:
                db.rollback()
                raise Exception(f"Ошибка при создании комментария: {str(seq_error)}")
        else:
            raise e

def delete_comment(db: Session, comment_id: int):
    db_comment = get_comment(db, comment_id)
    if not db_comment:
        return None
    db.delete(db_comment)
    db.commit()
    return db_comment

from .auth import hash_password

def get_user_by_login(db: Session, login: str):
    return db.query(models.User).filter(models.User.login == login).first()