from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi import Header
from fastapi.openapi.utils import get_openapi
from fastapi.params import Header as HeaderParam
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Order
from db.models import OrderItem
from schemas.order_schemas import OrderItemResponse
from schemas.order_schemas import OrderResponse


def HeaderNoSchema(*args: Any, **kwargs: Any) -> HeaderParam:
    return Header(*args, include_in_schema=False, **kwargs)  # type: ignore[no-any-return]


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Orders API",
        version="1.0",
        routes=app.routes,
        servers=[{"url": "/orders"}],
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BasicAuth": {"type": "http", "scheme": "basic"}
    }
    openapi_schema["security"] = [{"BasicAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


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
        created_at=db_order.created_at,
        updated_at=db_order.updated_at,
    )


def build_customer_orders_response(
    db: Session, customer_id: UUID | str
) -> list[OrderResponse]:
    query = select(Order).where(Order.customer_id == customer_id)
    db_orders = db.scalars(query)

    return [build_order_response(db, db_order) for db_order in db_orders]
