from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Customer, Order
from ..schemas import CustomerCreate, CustomerOut, CustomerUpdate, Page

router = APIRouter(prefix="/customers", tags=["Клієнти"], dependencies=[Depends(get_current_user)])


def _out(db: Session, c: Customer) -> CustomerOut:
    out = CustomerOut.model_validate(c)
    out.orders_count = db.scalar(select(func.count()).where(Order.customer_id == c.id)) or 0
    return out


def _get(db: Session, customer_id: int) -> Customer:
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Клієнта {customer_id} не знайдено")
    return c


def _check_email(db: Session, email: str, exclude_id: int | None = None):
    q = select(Customer.id).where(Customer.email == email.lower())
    if exclude_id:
        q = q.where(Customer.id != exclude_id)
    if db.scalar(q):
        raise HTTPException(status.HTTP_409_CONFLICT, "Клієнт з таким email вже існує")


@router.get("", response_model=Page[CustomerOut], summary="Список клієнтів з пошуком")
def list_customers(
    search: str | None = Query(None, description="Ім'я, email або телефон"),
    city: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Customer)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(
            or_(
                func.lower(Customer.full_name).like(like),
                func.lower(Customer.email).like(like),
                Customer.phone.like(like),
            )
        )
    if city:
        q = q.where(Customer.city == city)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Customer.full_name).offset((page - 1) * limit).limit(limit)).all()
    return Page(items=[_out(db, c) for c in rows], total=total, page=page, limit=limit)


@router.get("/{customer_id}", response_model=CustomerOut, summary="Клієнт за id")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return _out(db, _get(db, customer_id))


@router.post("", response_model=CustomerOut, status_code=201, summary="Створити клієнта")
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    _check_email(db, data.email)
    c = Customer(**{**data.model_dump(), "email": data.email.lower()})
    db.add(c)
    db.commit()
    db.refresh(c)
    return _out(db, c)


@router.put("/{customer_id}", response_model=CustomerOut, summary="Оновити клієнта")
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    c = _get(db, customer_id)
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes:
        changes["email"] = changes["email"].lower()
        _check_email(db, changes["email"], customer_id)
    for k, v in changes.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _out(db, c)


@router.delete("/{customer_id}", status_code=204, summary="Видалити клієнта")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    c = _get(db, customer_id)
    if db.scalar(select(func.count()).where(Order.customer_id == customer_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "У клієнта є замовлення — видалення неможливе")
    db.delete(c)
    db.commit()
    return Response(status_code=204)
