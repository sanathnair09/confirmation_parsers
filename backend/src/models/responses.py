from pydantic import BaseModel


class RobinhoodResponse(BaseModel):
    symbol: str
    action: str  # Buy or Sell
    trade_date: str
    settle_date: str
    account_type: str
    price: float
    quantity: int
    principal: float
    commission: float
    contract_fee: float
    transaction_fee: float
    net_amount: float
    market: str  # Market type, e.g., "NASDAQ"
    cap: str  # Capitalization type, e.g., "Large Cap"
    us: str


class RobinhoodResponseList(BaseModel):
    data: list[RobinhoodResponse]


class FidelityResponse(BaseModel):
    date: str
    action: str
    symbol: str
    quantity: int
    price: float
    total: float
    order_no: str
    reference_no: str


class FidelityResponseList(BaseModel):
    data: list[FidelityResponse]


class HealthResponse(BaseModel):
    status: str
    ollama_available: bool
    message: str 