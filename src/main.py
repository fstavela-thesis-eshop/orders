import logging
from functools import partial

from fastapi import FastAPI

from api.helpers import custom_openapi
from api.orders import orders_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(orders_router, prefix="/orders", tags=["orders"])

app.openapi = partial(custom_openapi, app)  # type: ignore[method-assign]
