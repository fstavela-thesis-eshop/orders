import logging
import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from requests import patch
from requests.exceptions import HTTPError
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.helpers import HeaderNoSchema
from api.helpers import build_customer_orders_response
from api.helpers import build_order_response
from db.models import Order
from db.models import OrderItem
from db.session import get_db
from kafka.producer import produce_cancelled_order_event
from kafka.producer import produce_new_order_event
from kafka.producer import produce_updated_order_status_event
from schemas.order_schemas import OrderCreate
from schemas.order_schemas import OrderItemResponse
from schemas.order_schemas import OrderResponse
from schemas.order_schemas import OrderStatus
from schemas.order_schemas import OrderUpdate

logger = logging.getLogger(__name__)

INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8001")
INVENTORY_STOCK_URL = INVENTORY_BASE_URL + "/products/stock"


orders_router = APIRouter()


@orders_router.get("")
def get_orders(
    x_customer_id: Annotated[str, HeaderNoSchema()],
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> list[OrderResponse]:
    if x_is_admin:
        return [build_order_response(db, order) for order in db.scalars(select(Order))]
    return build_customer_orders_response(db, x_customer_id)  # type: ignore[no-any-return]


@orders_router.get("/customer/{customer_id}", responses={status.HTTP_403_FORBIDDEN: {}})
def get_customer_orders(
    customer_id: UUID,
    x_customer_id: Annotated[str, HeaderNoSchema()],
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> list[OrderResponse]:
    if str(customer_id) != x_customer_id and not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't list orders of a different customer",
        )

    return build_customer_orders_response(db, customer_id)  # type: ignore[no-any-return]


@orders_router.get(
    "/{order_id}",
    responses={status.HTTP_404_NOT_FOUND: {}},
)
def get_order(
    order_id: UUID,
    x_customer_id: Annotated[str, HeaderNoSchema()],
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    db_order = db.get(Order, order_id)
    if not db_order or (str(db_order.customer_id) != x_customer_id and not x_is_admin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    return build_order_response(db, db_order)


@orders_router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def create_order(
    input_order: OrderCreate,
    x_customer_id: Annotated[str, HeaderNoSchema()],
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    if str(input_order.customer_id) != x_customer_id and not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't create an order for a different customer",
        )

    request_data = [
        {"id": str(item.product_id), "stock_quantity_dif": -item.quantity}
        for item in input_order.items
    ]
    try:
        response = patch(
            INVENTORY_STOCK_URL, json=request_data, headers={"x-is-admin": "true"}
        )
        response.raise_for_status()
        response_data = response.json()
        products_data_by_id = {product["id"]: product for product in response_data}
    except HTTPError as err:
        raise HTTPException(
            status_code=err.response.status_code, detail=err.response.json()["detail"]
        ) from err

    total_price = sum(
        products_data_by_id[str(item.product_id)]["price"] * item.quantity
        for item in input_order.items
    )
    db_order = Order(
        customer_id=input_order.customer_id, total_price=total_price, status="created"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    response_items = []
    for item in input_order.items:
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            unit_price=products_data_by_id[str(item.product_id)]["price"],
            quantity=item.quantity,
        )
        db.add(db_item)
        response_items.append(
            OrderItemResponse(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=db_item.unit_price,
                total_price=item.quantity * db_item.unit_price,
            )
        )

    db.commit()

    response = OrderResponse(
        order_id=db_order.id,
        customer_id=input_order.customer_id,
        items=response_items,
        total_price=total_price,
        status=OrderStatus.CREATED,
        created_at=db_order.created_at,
        updated_at=db_order.updated_at,
    )
    produce_new_order_event(response)
    return response


@orders_router.patch(
    "/{order_id}",
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def update_order_status(
    order_id: UUID,
    update_input: OrderUpdate,
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_order = db.get(Order, order_id)
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if db_order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canceled order can't be updated",
        )

    db_order.status = update_input.status
    db.commit()
    db.refresh(db_order)

    response = build_order_response(db, db_order)
    produce_updated_order_status_event(response)
    return response


@orders_router.delete(
    "/{order_id}",
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def cancel_order(
    order_id: UUID,
    x_customer_id: Annotated[str, HeaderNoSchema()],
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    db_order = db.get(Order, order_id)
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if str(db_order.customer_id) != x_customer_id and not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't cancel an order for a different customer",
        )

    if db_order.status not in (OrderStatus.CREATED, OrderStatus.PAID):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Order can't be cancelled anymore"
        )

    query = select(OrderItem).where(OrderItem.order_id == db_order.id)
    db_items = db.scalars(query).all()
    logger.warning(db_items)
    request_data = [
        {"id": str(db_item.product_id), "stock_quantity_dif": db_item.quantity}
        for db_item in db_items
    ]
    patch(INVENTORY_STOCK_URL, json=request_data, headers={"x-is-admin": "true"})

    db_order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(db_order)

    logger.warning(db_items)

    response = build_order_response(db, db_order, db_items=db_items)
    produce_cancelled_order_event(response)
    return response
