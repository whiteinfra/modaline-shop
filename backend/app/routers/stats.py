from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Customer, Order, Payment, Product
from ..schemas import Stats

router = APIRouter(prefix="/stats", tags=["Статистика"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=Stats, summary="Зведені показники для дашборду")
def stats(db: Session = Depends(get_db)):
    by_status = dict(db.execute(select(Order.status, func.count()).group_by(Order.status)).all())
    revenue = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "success"))
    return Stats(
        products=db.scalar(select(func.count(Product.id))),
        customers=db.scalar(select(func.count(Customer.id))),
        orders=db.scalar(select(func.count(Order.id))),
        revenue=float(revenue),
        orders_by_status=by_status,
        low_stock=db.scalar(select(func.count(Product.id)).where(Product.stock <= 2)),
    )
