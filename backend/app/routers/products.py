from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import OrderItem, Product
from ..schemas import Page, ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["Товари"])
SORTS = {
    "name": Product.name.asc(),
    "price": Product.price.asc(),
    "-price": Product.price.desc(),
    "stock": Product.stock.asc(),
    "-created": Product.created_at.desc(),
}


def _get(db: Session, product_id: int) -> Product:
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Товар {product_id} не знайдено")
    return p


def _check_sku(db: Session, sku: str, exclude_id: int | None = None):
    q = select(Product.id).where(Product.sku == sku)
    if exclude_id:
        q = q.where(Product.id != exclude_id)
    if db.scalar(q):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Товар з артикулом {sku} вже існує")


@router.get("", response_model=Page[ProductOut], summary="Список товарів з фільтрами і пагінацією")
def list_products(
    search: str | None = Query(None, description="Пошук за назвою або артикулом"),
    category: str | None = None,
    size: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    in_stock: bool | None = None,
    sort: Literal["name", "price", "-price", "stock", "-created"] = "name",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Product)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(or_(func.lower(Product.name).like(like), func.lower(Product.sku).like(like)))
    if category:
        q = q.where(Product.category == category)
    if size:
        q = q.where(Product.size == size)
    if min_price is not None:
        q = q.where(Product.price >= min_price)
    if max_price is not None:
        q = q.where(Product.price <= max_price)
    if in_stock is not None:
        q = q.where(Product.stock > 0 if in_stock else Product.stock == 0)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(SORTS[sort], Product.id).offset((page - 1) * limit).limit(limit)).all()
    return Page(items=items, total=total, page=page, limit=limit)


@router.get("/categories", response_model=list[str], summary="Перелік категорій")
def categories(db: Session = Depends(get_db)):
    return db.scalars(select(Product.category).distinct().order_by(Product.category)).all()


@router.get("/{product_id}", response_model=ProductOut, summary="Товар за id")
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _get(db, product_id)


@router.post(
    "", response_model=ProductOut, status_code=201, summary="Створити товар", dependencies=[Depends(get_current_user)]
)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    _check_sku(db, data.sku)
    p = Product(**{**data.model_dump(), "price": Decimal(str(data.price))})
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put(
    "/{product_id}", response_model=ProductOut, summary="Оновити товар", dependencies=[Depends(get_current_user)]
)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    p = _get(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    if "sku" in changes:
        _check_sku(db, changes["sku"], product_id)
    if "price" in changes:
        changes["price"] = Decimal(str(changes["price"]))
    for k, v in changes.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{product_id}", status_code=204, summary="Видалити товар", dependencies=[Depends(get_current_user)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = _get(db, product_id)
    if db.scalar(select(func.count()).where(OrderItem.product_id == product_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Товар є в замовленнях — видалення неможливе")
    db.delete(p)
    db.commit()
    return Response(status_code=204)
