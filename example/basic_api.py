"""Example API used in Mockture integration examples."""

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field


class CreateOrderRequest(BaseModel):
    item_id: str = Field(min_length=1)
    quantity: int = Field(ge=1, le=100)


class OrderResponse(BaseModel):
    order_id: str
    status: str


app = FastAPI(title="Mockture Example API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(payload: CreateOrderRequest) -> OrderResponse:
    if payload.item_id == "FAIL":
        raise HTTPException(status_code=409, detail="Item is unavailable")

    return OrderResponse(order_id=f"ord-{payload.item_id.lower()}-001", status="created")

