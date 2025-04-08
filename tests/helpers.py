from datetime import datetime
from json import dumps
from random import choices
from random import randint
from random import uniform
from string import ascii_letters
from string import digits
from string import punctuation
from uuid import UUID
from uuid import uuid4

from requests import Response

from schemas.order_schemas import OrderItemResponse
from schemas.order_schemas import OrderResponse
from src.db.models import Order
from src.db.models import OrderItem


def gen_str(
    length: int = 10,
    *,
    use_letters: bool = True,
    use_digits: bool = True,
    use_punctuation: bool = True,
) -> str:
    symbols = ""
    if use_letters:
        symbols += ascii_letters
    if use_digits:
        symbols += digits
    if use_punctuation:
        symbols += punctuation
    return "".join(choices(symbols, k=length))


def gen_headers(
    *, customer_id: UUID | None = None, is_admin: bool = False
) -> dict[str, str]:
    return {
        "x-customer-id": str(customer_id or uuid4()),
        "x-is-admin": str(is_admin).lower(),
    }


def generate_random_db_item(order_id: UUID) -> OrderItem:
    return OrderItem(
        order_id=order_id,
        product_id=uuid4(),
        unit_price=round(uniform(10, 1000), 2),
        quantity=randint(1, 100),
    )


def generate_random_db_order(customer_id: UUID | None = None) -> Order:
    return Order(
        id=uuid4(),
        customer_id=customer_id or uuid4(),
        total_price=0,
        status="created",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def build_mock_item_response() -> OrderItemResponse:
    quantity = randint(1, 100)
    unit_price = round(uniform(10, 1000), 2)
    return OrderItemResponse(
        product_id=uuid4(),
        quantity=quantity,
        unit_price=unit_price,
        total_price=quantity * unit_price,
    )


def build_mock_order_response() -> OrderResponse:
    mock_item_response = build_mock_item_response()
    return OrderResponse(
        customer_id=uuid4(),
        order_id=uuid4(),
        items=[mock_item_response],
        total_price=mock_item_response.total_price,
        status="created",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def build_mock_product_response(product_id: str) -> Response:
    response = Response()
    response.status_code = 200
    response._content = dumps(
        [
            {
                "id": product_id,
                "name": gen_str(),
                "description": gen_str(50),
                "category_id": str(uuid4()),
                "price": round(uniform(10, 1000), 2),
                "stock_quantity": randint(1, 100),
            }
        ]
    ).encode("utf-8")

    return response


def generate_create_item_data(product_id: str) -> dict[str, str | int]:
    return {
        "product_id": product_id,
        "quantity": randint(1, 100),
    }


def generate_create_order_data(
    *, customer_id: str, product_id: str
) -> dict[str, str | list[dict[str, str | int]]]:
    return {
        "customer_id": customer_id,
        "items": [generate_create_item_data(product_id)],
    }


def generate_update_order_data() -> dict[str, str]:
    return {"status": "paid"}
