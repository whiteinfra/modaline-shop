from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Order, Payment
from ..schemas import Page, PaymentCreate, PaymentOut, PaymentUpdate
from .orders import load, paid_sum

router = APIRouter(prefix="/payments", tags=["Платежі"], dependencies=[Depends(get_current_user)])


def _sync_order(db: Session, order_id: int):
    """Якщо успішні платежі покривають суму — замовлення стає оплаченим."""
    o = load(db, order_id)
    if o.status == "new" and paid_sum(o) >= Decimal(str(o.total)):
        o.status = "paid"


def _get(db: Session, payment_id: int) -> Payment:
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Платіж {payment_id} не знайдено")
    return p


@router.get("", response_model=Page[PaymentOut], summary="Список платежів")
def list_payments(
    order_id: int | None = None,
    status_: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Payment)
    if order_id:
        q = q.where(Payment.order_id == order_id)
    if status_:
        q = q.where(Payment.status == status_)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Payment.id.desc()).offset((page - 1) * limit).limit(limit)).all()
    return Page(items=rows, total=total, page=page, limit=limit)


@router.get("/{payment_id}", response_model=PaymentOut, summary="Платіж за id")
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    return _get(db, payment_id)


@router.post("", response_model=PaymentOut, status_code=201, summary="Зареєструвати платіж")
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    order = db.get(Order, data.order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Замовлення {data.order_id} не знайдено")
    if order.status == "cancelled":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Замовлення скасовано — оплата неможлива")
    p = Payment(
        **{**data.model_dump(), "amount": Decimal(str(data.amount))},
        paid_at=datetime.now() if data.status == "success" else None,
    )
    db.add(p)
    db.flush()
    _sync_order(db, data.order_id)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{payment_id}", response_model=PaymentOut, summary="Змінити статус платежу")
def update_payment(payment_id: int, data: PaymentUpdate, db: Session = Depends(get_db)):
    p = _get(db, payment_id)
    p.status = data.status
    p.paid_at = datetime.now() if data.status == "success" else None
    db.flush()
    _sync_order(db, p.order_id)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{payment_id}", status_code=204, summary="Видалити платіж (крім успішних)")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    p = _get(db, payment_id)
    if p.status == "success":
        raise HTTPException(status.HTTP_409_CONFLICT, "Успішний платіж видаляти не можна")
    db.delete(p)
    db.commit()
    return Response(status_code=204)
