import io
import qrcode
from fastapi import APIRouter, Response, Depends
from ..auth import require_roles

FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdhZcExx6LSIXxk0ub55mSu-WIh23WYdGG9HY5EZhLDo7P8eA/viewform?usp=sf_link"

router = APIRouter()

@router.get("/feedback", response_class=Response)
def feedback_qr(current=Depends(require_roles('Оператор','Специалист','Менеджер','Менеджер по качеству','Заказчик'))):
    img = qrcode.make(FEEDBACK_URL)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
