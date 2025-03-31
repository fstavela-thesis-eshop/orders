from fastapi import FastAPI

from api.orders import orders_router

app = FastAPI()
app.include_router(orders_router, prefix="/orders", tags=["orders"])
