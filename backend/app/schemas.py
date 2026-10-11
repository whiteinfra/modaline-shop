"""Pydantic-схеми запитів і відповідей (валідація + документація OpenAPI)."""

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int


# ---- auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, examples=["Passw0rd!"])
    full_name: str = Field(min_length=2, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- products
class ProductBase(BaseModel):
    sku: str = Field(min_length=3, max_length=30, examples=["HD-BAS-L-GR"])
    name: str = Field(min_length=2, max_length=150, examples=["Худі оверсайз «Basic»"])
    category: str = Field(min_length=2, max_length=60, examples=["Худі"])
    size: Literal["XS", "S", "M", "L", "XL", "XXL"]
    color: str = Field(min_length=2, max_length=30, examples=["сірий"])
    price: float = Field(gt=0, examples=[1290])
    stock: int = Field(ge=0, examples=[5])
    description: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(None, min_length=3, max_length=30)
    name: str | None = Field(None, min_length=2, max_length=150)
    category: str | None = None
    size: Literal["XS", "S", "M", "L", "XL", "XXL"] | None = None
    color: str | None = None
    price: float | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)
    description: str | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ---- customers
class CustomerBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=100, examples=["Ірина Петренко"])
    email: EmailStr
    phone: str | None = Field(None, pattern=r"^\+?\d{10,13}$", examples=["+380671234567"])
    city: str | None = Field(None, max_length=60, examples=["Київ"])


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=r"^\+?\d{10,13}$")
    city: str | None = None


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    orders_count: int = 0


# ---- orders
OrderStatus = Literal["new", "paid", "shipped", "completed", "cancelled"]


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=100)


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemIn] = Field(min_length=1)
    comment: str | None = None


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    comment: str | None = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: str
    sku: str
    quantity: int
    unit_price: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    customer_name: str
    status: OrderStatus
    total: float
    paid: float
    comment: str | None
    created_at: datetime
    items: list[OrderItemOut] = []


# ---- payments
class PaymentCreate(BaseModel):
    order_id: int
    amount: float = Field(gt=0)
    method: Literal["card", "cash", "transfer"]
    status: Literal["pending", "success", "failed"] = "success"


class PaymentUpdate(BaseModel):
    status: Literal["pending", "success", "failed"]


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    amount: float
    method: str
    status: str
    paid_at: datetime | None
    created_at: datetime


class Stats(BaseModel):
    products: int
    customers: int
    orders: int
    revenue: float
    orders_by_status: dict[str, int]
    low_stock: int
