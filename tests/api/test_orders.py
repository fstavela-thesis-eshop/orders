import logging
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock.plugin import MockerFixture
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import OrderItem
from schemas.order_schemas import OrderResponse
from schemas.order_schemas import OrderStatus
from src.db.models import Order

# from tests.helpers import generate_change_stock_quantity_data
# from tests.helpers import generate_create_product_data
# from tests.helpers import generate_random_db_category
# from tests.helpers import generate_random_db_product
# from tests.helpers import validate_db_product
# from tests.helpers import validate_product_response
from tests.helpers import build_mock_order_response
from tests.helpers import build_mock_product_response

# from src.db.models import Category
# from src.db.models import Product
from tests.helpers import gen_headers
from tests.helpers import generate_create_order_data
from tests.helpers import generate_random_db_order
from tests.helpers import generate_update_order_data

logger = logging.getLogger(__name__)


def test_get_orders_as_admin(
    api_client: TestClient,
    mock_db: MagicMock,
    mocker: MockerFixture,
) -> None:
    order = generate_random_db_order()
    mock_response = build_mock_order_response()

    def _scalars(query: Select[Order]) -> list[Order]:
        assert str(query.compile()) == str(select(Order).compile())
        return [order]

    def _build_response(_: Session, input_order: Order) -> OrderResponse:
        assert input_order == order
        return mock_response

    mock_db.scalars = _scalars
    mocker.patch("api.orders.build_order_response", _build_response)

    response = api_client.get(
        "/orders",
        headers=gen_headers(is_admin=True),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    assert OrderResponse.model_validate(response_json[0]) == mock_response


def test_get_orders_as_non_admin(
    api_client: TestClient,
    mock_db: MagicMock,
    mocker: MockerFixture,
) -> None:
    customer_id = uuid4()
    order = generate_random_db_order()
    mock_response = build_mock_order_response()

    def _scalars(query: Select[Order]) -> list[Order]:
        assert str(query.compile()) == str(
            select(Order).where(Order.customer_id == customer_id).compile()
        )
        return [order]

    def _build_response(_: Session, input_order: Order) -> OrderResponse:
        assert input_order == order
        return mock_response

    mock_db.scalars = _scalars
    mocker.patch("api.helpers.build_order_response", _build_response)

    response = api_client.get(
        "/orders",
        headers=gen_headers(customer_id=customer_id, is_admin=False),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    assert OrderResponse.model_validate(response_json[0]) == mock_response


@pytest.mark.parametrize("customer_id", ("str", "123", str(uuid4()) + "a"))
@pytest.mark.parametrize("is_admin", (True, False))
def test_get_orders_by_customer_id_wrong_id(
    api_client: TestClient, customer_id: str, is_admin: bool
) -> None:
    response = api_client.get(
        f"/orders/customer/{customer_id}",
        headers=gen_headers(is_admin=is_admin),
    )
    assert response.status_code == 422


def test_get_orders_by_customer_id_different_customer_as_non_admin(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        f"/orders/customer/{str(uuid4())}",
        headers=gen_headers(is_admin=False),
    )
    assert response.status_code == 403


def test_get_orders_by_customer_id_different_customer_as_admin(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture
) -> None:
    customer_id = uuid4()
    order = generate_random_db_order()
    mock_response = build_mock_order_response()

    def _scalars(query: Select[Order]) -> list[Order]:
        assert str(query.compile()) == str(
            select(Order).where(Order.customer_id == customer_id).compile()
        )
        return [order]

    def _build_response(_: Session, input_order: Order) -> OrderResponse:
        assert input_order == order
        return mock_response

    mock_db.scalars = _scalars
    mocker.patch("api.helpers.build_order_response", _build_response)

    response = api_client.get(
        f"/orders/customer/{str(customer_id)}",
        headers=gen_headers(is_admin=True),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    assert OrderResponse.model_validate(response_json[0]) == mock_response


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_orders_by_customer_id_correct(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    customer_id = uuid4()
    order = generate_random_db_order()
    mock_response = build_mock_order_response()

    def _scalars(query: Select[Order]) -> list[Order]:
        assert str(query.compile()) == str(
            select(Order).where(Order.customer_id == customer_id).compile()
        )
        return [order]

    def _build_response(_: Session, input_order: Order) -> OrderResponse:
        assert input_order == order
        return mock_response

    mock_db.scalars = _scalars
    mocker.patch("api.helpers.build_order_response", _build_response)

    response = api_client.get(
        f"/orders/customer/{str(customer_id)}",
        headers=gen_headers(customer_id=customer_id, is_admin=is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    assert OrderResponse.model_validate(response_json[0]) == mock_response


@pytest.mark.parametrize("order_id", ("str", "123", str(uuid4()) + "a"))
@pytest.mark.parametrize("is_admin", (True, False))
def test_get_order_by_id_wrong_id(
    api_client: TestClient, order_id: str, is_admin: bool
) -> None:
    response = api_client.get(
        f"/orders/{order_id}",
        headers=gen_headers(is_admin=is_admin),
    )
    assert response.status_code == 422


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_order_by_id_not_found(
    api_client: TestClient, mock_db: MagicMock, is_admin: bool
) -> None:
    order_id = uuid4()

    def _get(_: Any, input_order_id: UUID) -> None:
        assert input_order_id == order_id
        return None

    mock_db.get = _get

    response = api_client.get(
        f"/orders/{str(order_id)}",
        headers=gen_headers(is_admin=is_admin),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_order_by_id_correct(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    order = generate_random_db_order()
    mock_response = build_mock_order_response()

    def _get(_: Any, order_id: UUID) -> Order:
        assert order_id == order.id
        return order

    def _build_response(_: Session, input_order: Order) -> OrderResponse:
        assert input_order == order
        return mock_response

    mock_db.get = _get
    mocker.patch("api.orders.build_order_response", _build_response)

    response = api_client.get(
        f"/orders/{str(order.id)}",
        headers=gen_headers(customer_id=order.customer_id, is_admin=is_admin),  # type: ignore[arg-type]
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)
    assert OrderResponse.model_validate(response_json) == mock_response


def test_create_order(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture
) -> None:
    customer_id = uuid4()
    product_id = str(uuid4())
    order_data = generate_create_order_data(
        customer_id=str(customer_id), product_id=product_id
    )
    orders = []

    def _refresh(order: Order) -> None:
        assert order.customer_id == customer_id
        assert order.status == OrderStatus.CREATED
        order.id = uuid4()  # type: ignore[assignment]
        order.created_at = datetime.now()  # type: ignore[assignment]
        order.updated_at = datetime.now()  # type: ignore[assignment]
        orders.append(order)

    mock_db.refresh = _refresh
    mocker.patch(
        "api.orders.patch", return_value=build_mock_product_response(product_id)
    )
    produce_event = mocker.patch("api.orders.produce_new_order_event")

    response = api_client.post(
        "/orders/create",
        headers=gen_headers(customer_id=customer_id, is_admin=False),
        json=order_data,
    )

    assert len(orders) == 1
    assert mock_db.commit.call_count == 2
    produce_event.assert_called_once()

    assert response.status_code == 201
    response_json = response.json()
    assert isinstance(response_json, dict)

    serialized_response = OrderResponse.model_validate(response_json)
    assert serialized_response.order_id == orders[0].id
    assert serialized_response.customer_id == customer_id
    assert serialized_response.status == OrderStatus.CREATED
    assert serialized_response.created_at == orders[0].created_at
    assert serialized_response.updated_at == orders[0].updated_at


@pytest.mark.parametrize("order_id", ("str", "123", str(uuid4()) + "a"))
def test_update_order_wrong_id(api_client: TestClient, order_id: str) -> None:
    update_data = generate_update_order_data()

    response = api_client.patch(
        f"/orders/{order_id}",
        json=update_data,
        headers=gen_headers(is_admin=True),
    )
    assert response.status_code == 422


def test_update_order_forbidden(api_client: TestClient) -> None:
    update_data = generate_update_order_data()

    response = api_client.patch(
        f"/orders/{str(uuid4())}", headers=gen_headers(is_admin=False), json=update_data
    )
    assert response.status_code == 403


def test_update_order_not_found(api_client: TestClient, mock_db: MagicMock) -> None:
    order_id = str(uuid4())

    def _get_order(_: Any, input_order_id: UUID) -> None:
        assert str(input_order_id) == order_id
        return None

    mock_db.get = _get_order

    update_data = generate_update_order_data()

    response = api_client.patch(
        f"/orders/{order_id}",
        json=update_data,
        headers=gen_headers(is_admin=True),
    )
    assert response.status_code == 404


def test_update_order_correct(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture
) -> None:
    mock_order = generate_random_db_order()
    orig_id = mock_order.id
    mock_response = build_mock_order_response()

    def _build_response(_: Session, input_order: Order) -> OrderResponse:
        assert input_order == mock_order
        return mock_response

    def _get_order(_: Any, input_order_id: str) -> Order:
        assert input_order_id == mock_order.id
        return mock_order

    mock_db.get = _get_order
    mocker.patch("api.orders.build_order_response", _build_response)
    produce_event = mocker.patch("api.orders.produce_updated_order_status_event")

    update_data = generate_update_order_data()

    response = api_client.patch(
        f"/orders/{str(mock_order.id)}",
        json=update_data,
        headers=gen_headers(is_admin=True),
    )

    produce_event.assert_called_once()
    mock_db.commit.assert_called_once()
    assert mock_order.id == orig_id
    assert mock_order.status == update_data["status"]

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)
    assert OrderResponse.model_validate(response_json) == mock_response


def test_cancel_order(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture
) -> None:
    customer_id = uuid4()
    mock_order = generate_random_db_order(customer_id)
    mock_response = build_mock_order_response()

    def _get_order(_: Any, input_order_id: str) -> Order:
        assert input_order_id == mock_order.id
        return mock_order

    def _build_response(
        _: Session,
        input_order: Order,
        db_items: list[OrderItem],  # noqa: ARG001
    ) -> OrderResponse:
        assert input_order == mock_order
        return mock_response

    def _refresh(order: Order) -> None:
        assert order == mock_order

    mock_db.get = _get_order
    mock_db.refresh = _refresh
    mocker.patch("api.orders.build_order_response", _build_response)
    mocker.patch(
        "api.orders.patch", return_value=build_mock_product_response(str(uuid4()))
    )
    produce_event = mocker.patch("api.orders.produce_cancelled_order_event")

    response = api_client.delete(
        f"/orders/{str(mock_order.id)}",
        headers=gen_headers(customer_id=customer_id, is_admin=False),
    )

    mock_db.commit.assert_called_once()
    produce_event.assert_called_once()
    assert mock_order.status == OrderStatus.CANCELLED

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)
    assert OrderResponse.model_validate(response_json) == mock_response
