from unittest.mock import MagicMock

from sqlalchemy import Select
from sqlalchemy import select

from schemas.order_schemas import OrderItemResponse
from schemas.order_schemas import OrderResponse
from src.api.helpers import build_order_response
from src.db.models import OrderItem
from tests.helpers import generate_random_db_item
from tests.helpers import generate_random_db_order


def test_build_order_response_without_items(mock_db: MagicMock) -> None:
    order = generate_random_db_order()
    item = generate_random_db_item(order.id)  # type: ignore[arg-type]

    def _scalars(query: Select[OrderItem]) -> list[OrderItem]:
        assert str(query.compile()) == str(
            select(OrderItem).where(OrderItem.order_id == order.id).compile()
        )
        return [item]

    mock_db.scalars = _scalars

    expected_response_item = OrderItemResponse(
        product_id=item.product_id,
        quantity=item.quantity,
        unit_price=item.unit_price,
        total_price=item.quantity * item.unit_price,
    )
    expected_response = OrderResponse(
        customer_id=order.customer_id,
        order_id=order.id,
        items=[expected_response_item],
        total_price=expected_response_item.total_price,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

    assert build_order_response(mock_db, order) == expected_response


def test_build_order_response_with_single_item(mock_db: MagicMock) -> None:
    order = generate_random_db_order()
    item = generate_random_db_item(order.id)  # type: ignore[arg-type]

    expected_response_item = OrderItemResponse(
        product_id=item.product_id,
        quantity=item.quantity,
        unit_price=item.unit_price,
        total_price=item.quantity * item.unit_price,
    )
    expected_response = OrderResponse(
        customer_id=order.customer_id,
        order_id=order.id,
        items=[expected_response_item],
        total_price=expected_response_item.total_price,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

    assert build_order_response(mock_db, order, db_items=[item]) == expected_response
    mock_db.scalars.assert_not_called()


def test_build_order_response_with_multiple_items(mock_db: MagicMock) -> None:
    order = generate_random_db_order()
    item1 = generate_random_db_item(order.id)  # type: ignore[arg-type]
    item2 = generate_random_db_item(order.id)  # type: ignore[arg-type]

    expected_response_item1 = OrderItemResponse(
        product_id=item1.product_id,
        quantity=item1.quantity,
        unit_price=item1.unit_price,
        total_price=item1.quantity * item1.unit_price,
    )
    expected_response_item2 = OrderItemResponse(
        product_id=item2.product_id,
        quantity=item2.quantity,
        unit_price=item2.unit_price,
        total_price=item2.quantity * item2.unit_price,
    )
    expected_response = OrderResponse(
        customer_id=order.customer_id,
        order_id=order.id,
        items=[expected_response_item1, expected_response_item2],
        total_price=expected_response_item1.total_price
        + expected_response_item2.total_price,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

    assert (
        build_order_response(mock_db, order, db_items=[item1, item2])
        == expected_response
    )
    mock_db.scalars.assert_not_called()
