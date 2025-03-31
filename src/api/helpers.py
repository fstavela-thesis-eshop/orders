from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Order
from db.models import OrderItem
from schemas.order_schemas import OrderItemResponse
from schemas.order_schemas import OrderResponse


def build_order_response(
    db: Session,
    db_order: Order,
    *,
    db_items: Iterable[OrderItem] | None = None,
) -> OrderResponse:
    if db_items is None:
        query = select(OrderItem).where(OrderItem.order_id == db_order.id)
        db_items = db.scalars(query)

    response_items = []
    total_price = 0
    for db_item in db_items:
        product_price = db_item.quantity * db_item.unit_price
        total_price += product_price
        response_items.append(
            OrderItemResponse(
                product_id=db_item.product_id,
                quantity=db_item.quantity,
                unit_price=db_item.unit_price,
                total_price=product_price,
            )
        )

    return OrderResponse(
        order_id=db_order.id,
        customer_id=db_order.customer_id,
        items=response_items,
        total_price=total_price,
        status=db_order.status,
    )


def build_customer_orders_response(
    db: Session, customer_id: UUID | str
) -> list[OrderResponse]:
    query = select(Order).where(Order.customer_id == customer_id)
    db_orders = db.scalars(query)

    return [build_order_response(db, db_order) for db_order in db_orders]
