from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    SENT = "sent"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int

    model_config = ConfigDict(extra="forbid")


class OrderItemResponse(OrderItemBase):
    unit_price: float
    total_price: float


class OrderBase(BaseModel):
    customer_id: UUID

    model_config = ConfigDict(extra="forbid")


class OrderCreate(OrderBase):
    items: list[OrderItemBase]


class OrderUpdate(BaseModel):
    status: OrderStatus

    model_config = ConfigDict(extra="forbid")


class OrderResponse(OrderBase):
    order_id: UUID
    items: list[OrderItemResponse]
    total_price: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderEvent(OrderResponse):
    message: str
