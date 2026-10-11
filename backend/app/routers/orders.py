from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Customer, Order, OrderItem, Product, User
from ..schemas import OrderCreate, OrderItemOut, OrderOut, OrderUpdate, Page

router = APIRouter(prefix="/orders", tags=["Замовлення"], dependencies=[Depends(get_current_user)])

TRANSITIONS = {
    "new": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


def paid_sum(order: Order) -> Decimal:
    return sum((Decimal(str(p.amount)) for p in order.payments if p.status == "success"), Decimal(0))


def to_out(o: Order) -> OrderOut:
    return OrderOut(
        id=o.id,
        customer_id=o.customer_id,
        customer_name=o.customer.full_name,
        status=o.status,
        total=float(o.total),
        paid=float(paid_sum(o)),
        comment=o.comment,
        created_at=o.created_at,
        items=[
            OrderItemOut(
                id=i.id,
                product_id=i.product_id,
                product_name=i.product.name,
                sku=i.product.sku,
                quantity=i.quantity,
                unit_price=float(i.unit_price),
            )
            for i in o.items
        ],
    )


def load(db: Session, order_id: int) -> Order:
    o = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payments),
            selectinload(Order.customer),
        )
    )
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Замовлення {order_id} не знайдено")
    return o


def restore_stock(order: Order):
    for i in order.items:
        i.product.stock += i.quantity


@router.get("", response_model=Page[OrderOut], summary="Список замовлень з фільтрами")
def list_orders(
    status_: str | None = Query(None, alias="status"),
    customer_id: int | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Order)
    if status_:
        q = q.where(Order.status == status_)
    if customer_id:
        q = q.where(Order.customer_id == customer_id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(
        q.options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payments),
            selectinload(Order.customer),
        )
        .order_by(Order.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return Page(items=[to_out(o) for o in rows], total=total, page=page, limit=limit)


@router.get("/{order_id}", response_model=OrderOut, summary="Замовлення з позиціями")
def get_order(order_id: int, db: Session = Depends(get_db)):
    return to_out(load(db, order_id))


@router.post("", response_model=OrderOut, status_code=201, summary="Створити замовлення (списує залишки)")
def create_order(data: OrderCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(Customer, data.customer_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Клієнта {data.customer_id} не знайдено")
    order = Order(customer_id=data.customer_id, comment=data.comment, created_by=user.id, status="new")
    total = Decimal(0)
    for it in data.items:
        p = db.get(Product, it.product_id, with_for_update=True)
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Товар {it.product_id} не знайдено")
        if p.stock < it.quantity:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Недостатньо товару «{p.name}» ({p.sku}): є {p.stock}, потрібно {it.quantity}",
            )
        p.stock -= it.quantity
        order.items.append(OrderItem(product_id=p.id, quantity=it.quantity, unit_price=p.price))
        total += p.price * it.quantity
    order.total = total
    db.add(order)
    db.commit()
    return to_out(load(db, order.id))


@router.put("/{order_id}", response_model=OrderOut, summary="Змінити статус / коментар")
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    o = load(db, order_id)
    if data.status and data.status != o.status:
        if data.status not in TRANSITIONS[o.status]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Неможливий перехід статусу: {o.status} → {data.status}")
        if data.status == "paid" and paid_sum(o) < Decimal(str(o.total)):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Оплату не підтверджено: сума успішних платежів менша за суму замовлення"
            )
        if data.status == "cancelled":
            restore_stock(o)
        o.status = data.status
    if data.comment is not None:
        o.comment = data.comment
    db.commit()
    return to_out(load(db, order_id))


@router.delete("/{order_id}", status_code=204, summary="Видалити замовлення (лише нове або скасоване)")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    o = load(db, order_id)
    if o.status not in ("new", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Видаляти можна лише нові або скасовані замовлення")
    if o.status == "new":
        restore_stock(o)
    db.delete(o)
    db.commit()
    return Response(status_code=204)
