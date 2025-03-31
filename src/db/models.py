from uuid import uuid4

from sqlalchemy import UUID
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Order(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "orders"

    id = Column(
        UUID(as_uuid=True), nullable=False, unique=True, primary_key=True, default=uuid4
    )
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    total_price = Column(Float, nullable=False)
    status = Column(String(9), nullable=False)


class OrderItem(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "order_items"

    order_id: Column[UUID[str]] = Column(
        ForeignKey("orders.id"), nullable=False, primary_key=True, index=True
    )
    product_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
