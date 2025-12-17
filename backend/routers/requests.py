from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import date
from .. import models, crud, schemas, database
from ..auth import get_current_user, require_roles

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[schemas.RequestOut])
def read_requests(skip: int = 0, limit: int = 100, 
                  db: Session = Depends(get_db), 
                  current_user: models.User = Depends(get_current_user)):
    """Получить все заявки (доступно сотрудникам)"""
    if current_user.user_type == "Заказчик":
        raise HTTPException(status_code=403, detail="Заказчикам доступны только свои заявки")
    return crud.get_requests(db, skip=skip, limit=limit)

# ⚠️ ВАЖНО: Этот маршрут должен быть ВЫШЕ /{request_id}
@router.get("/search", response_model=list[schemas.RequestOut])
def search_requests(
    number: Optional[int] = Query(None, description="Номер заявки"),
    status: Optional[str] = Query(None, description="Статус"),
    tech_type: Optional[str] = Query(None, description="Тип оборудования"),
    client_id: Optional[int] = Query(None, description="ID клиента"),
    master_id: Optional[int] = Query(None, description="ID мастера"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Поиск заявок"""
    if current_user.user_type == "Заказчик":
        raise HTTPException(status_code=403, detail="Заказчикам доступен только поиск по своим заявкам через /client/my-requests")
    
    q = db.query(models.Request)
    if number is not None:
        q = q.filter(models.Request.request_id == number)
    if status is not None:
        q = q.filter(models.Request.request_status == status)
    if tech_type is not None:
        q = q.filter(models.Request.climate_tech_type == tech_type)
    if client_id is not None:
        q = q.filter(models.Request.client_id == client_id)
    if master_id is not None:
        q = q.filter(models.Request.master_id == master_id)
    results = q.all()
    if not results:
        # Возвращаем пустой список вместо ошибки
        return []
    return results

@router.get("/{request_id}", response_model=schemas.RequestOut)
def read_request(request_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    """Получить детали заявки"""
    db_request = crud.get_request(db, request_id)
    if db_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверка доступа для заказчиков
    if current_user.user_type == "Заказчик" and db_request.client_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой заявке")
    
    return db_request

@router.post("/", response_model=schemas.RequestOut)
def create_request(request: schemas.RequestCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    """Создать новую заявку"""
    if current_user.user_type == "Заказчик":
        raise HTTPException(status_code=403, detail="Заказчики создают заявки через /client/my-requests")
    return crud.create_request(db, request)

@router.put("/{request_id}", response_model=schemas.RequestOut)
def update_request(request_id: int, request_update: schemas.RequestUpdate, 
                   db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    """Обновить заявку"""
    if current_user.user_type == "Заказчик":
        raise HTTPException(status_code=403, detail="Заказчики не могут редактировать заявки")
    
    db_request = crud.update_request(db, request_id, request_update)
    if db_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return db_request

@router.delete("/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    """Удалить заявку"""
    if current_user.user_type != "Менеджер":
        raise HTTPException(status_code=403, detail="Только менеджеры могут удалять заявки")
    
    deleted = crud.delete_request(db, request_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return {"detail": "Удаление подтверждено: заявка удалена"}

@router.post("/{request_id}/assign", response_model=schemas.RequestOut)
def assign_specialist(request_id: int, data: schemas.AssignSpecialistIn, 
                      db: Session = Depends(get_db),
                      current_user: models.User = Depends(get_current_user)):
    """Назначить специалиста на заявку"""
    if current_user.user_type not in ["Менеджер", "Менеджер по качеству"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    upd = schemas.RequestUpdate(master_id=data.master_id)
    db_request = crud.update_request(db, request_id, upd)
    if db_request is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return db_request

@router.post("/{request_id}/extend", response_model=schemas.RequestOut)
def extend_deadline(request_id: int, data: schemas.ExtendDeadlineIn, 
                    db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    """Продлить срок выполнения заявки"""
    if current_user.user_type not in ["Менеджер", "Менеджер по качеству"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    upd = schemas.RequestUpdate(completion_date=data.new_completion_date)
    db_request = crud.update_request(db, request_id, upd)
    if db_request is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return db_request

@router.get("/stats/count")
def stats_count(db: Session = Depends(get_db), 
                current_user: models.User = Depends(get_current_user)):
    """Получить статистику по количеству заявок"""
    
    if current_user.user_type == "Заказчик":
        # Для заказчика - только его заявки
        total = db.query(func.count(models.Request.request_id)).filter(
            models.Request.client_id == current_user.user_id
        ).scalar()
        
        done = db.query(func.count(models.Request.request_id)).filter(
            and_(
                models.Request.client_id == current_user.user_id,
                models.Request.completion_date.isnot(None)
            )
        ).scalar()
    else:
        # Для сотрудников - все заявки
        total = db.query(func.count(models.Request.request_id)).scalar()
        
        done = db.query(func.count(models.Request.request_id)).filter(
            models.Request.completion_date.isnot(None)
        ).scalar()
    
    return {
        "total_requests": total or 0, 
        "completed_requests": done or 0
    }

@router.get("/stats/avg-time")
def stats_avg_time(db: Session = Depends(get_db), 
                   current_user: models.User = Depends(get_current_user)):
    """Получить среднее время выполнения заявок"""
    
    if current_user.user_type == "Заказчик":
        # Для заказчика - только его завершенные заявки
        completed_requests = db.query(models.Request).filter(
            and_(
                models.Request.client_id == current_user.user_id,
                models.Request.completion_date.isnot(None)
            )
        ).all()
    else:
        # Для сотрудников - все завершенные заявки
        completed_requests = db.query(models.Request).filter(
            models.Request.completion_date.isnot(None)
        ).all()
    
    total_days = 0
    count = 0
    
    for request in completed_requests:
        if request.start_date and request.completion_date:
            days = (request.completion_date - request.start_date).days
            if days >= 0:  # Учитываем даже если 0 дней
                total_days += days
                count += 1
    
    avg_days_float = total_days / count if count > 0 else 0
    
    return {
        "avg_repair_days": round(avg_days_float, 1),
        "count_completed": count,
        "total_days": total_days
    }

@router.get("/stats/by-problem-type")
def stats_by_problem_type(db: Session = Depends(get_db), 
                          current_user: models.User = Depends(get_current_user)):
    """Получить статистику по типам проблем"""
    
    if current_user.user_type == "Заказчик":
        # Для заказчика - только его заявки
        rows = db.query(
            models.Request.problem_description, 
            func.count(models.Request.request_id)
        ).filter(
            models.Request.client_id == current_user.user_id
        ).group_by(models.Request.problem_description).all()
    else:
        # Для сотрудников - все заявки
        rows = db.query(
            models.Request.problem_description, 
            func.count(models.Request.request_id)
        ).group_by(models.Request.problem_description).all()
    
    return [{"problem": r[0], "count": r[1]} for r in rows]

@router.get("/stats/by-tech")
def stats_by_tech(db: Session = Depends(get_db), 
                  current_user: models.User = Depends(get_current_user)):
    """Получить статистику по типам оборудования"""
    
    if current_user.user_type == "Заказчик":
        # Для заказчика - только его заявки
        rows = db.query(
            models.Request.climate_tech_type, 
            func.count(models.Request.request_id)
        ).filter(
            models.Request.client_id == current_user.user_id
        ).group_by(models.Request.climate_tech_type).all()
    else:
        # Для сотрудников - все заявки
        rows = db.query(
            models.Request.climate_tech_type, 
            func.count(models.Request.request_id)
        ).group_by(models.Request.climate_tech_type).all()
    
    return [{"tech_type": r[0], "count": r[1]} for r in rows]

# Импортируем case для debug эндпоинта
from sqlalchemy import case

@router.get("/debug/statuses")
def debug_statuses(db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    """Отладочный эндпоинт - показывает все статусы"""
    if current_user.user_type not in ["Менеджер", "Менеджер по качеству"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    statuses = db.query(
        models.Request.request_status,
        func.count(models.Request.request_id),
        func.sum(case((models.Request.completion_date.isnot(None), 1), else_=0))
    ).group_by(models.Request.request_status).all()
    
    all_requests = db.query(models.Request).all()
    
    return {
        "status_counts": [{"status": s[0], "count": s[1], "completed": s[2]} for s in statuses],
        "total_requests": len(all_requests),
        "completed_requests": sum(1 for r in all_requests if r.completion_date is not None)
    }