from typing import Optional, List, Tuple, TypedDict
from decimal import Decimal
from dataclasses import dataclass, fields
from enum import Enum
from pydantic import BaseModel, model_validator


class GqlChain(Enum):
    ARBITRUM = "ARBITRUM"
    AVALANCHE = "AVALANCHE"
    BASE = "BASE"
    FANTOM = "FANTOM"
    GNOSIS = "GNOSIS"
    MAINNET = "MAINNET"
    OPTIMISM = "OPTIMISM"
    POLYGON = "POLYGON"
    SEPOLIA = "SEPOLIA"
    ZKEVM = "ZKEVM"


DateRange = Tuple[int, int]


@dataclass
class TWAPResult:
    address: str
    twap_price: Optional[Decimal]

@dataclass
class TwapPrices:
    bpt_price: Decimal
    token_prices: List[TWAPResult]

class Token(BaseModel):
    address: str
    logoURI: str
    symbol: str
    weight: Optional[str]


class Gauge(BaseModel):
    address: str
    isKilled: bool
    relativeWeightCap: Optional[str]
    addedTimestamp: Optional[int]
    childGaugeAddress: Optional[str]


class Pool(BaseModel):
    id: str
    address: str
    chain: str
    type: str
    symbol: str
    gauge: Gauge
    tokens: List[Token]


class PropData(BaseModel):
    proposal: str
    proposalHash: str
    title: str
    proposalDeadline: int
    totalValue: float
    maxTotalValue: float
    voteCount: float
    valuePerVote: float
    maxValuePerVote: float
    bribes: List
    index: str


class TokenFee(BaseModel):
    symbol: str
    address: str
    paidProtocolFees: Optional[Decimal] = None

    @model_validator(mode="before")
    def cast(cls, values):
        fees = values["paidProtocolFees"]
        values["paidProtocolFees"] = Decimal(fees) if fees else Decimal(0)
        return values


class PoolSnapshot(BaseModel):
    timestamp: int
    protocolFee: str
    swapFees: str
    swapVolume: str
    liquidity: str
    address: str
    id: str
    symbol: str
    totalProtocolFeePaidInBPT: Optional[Decimal] = None
    tokens: List[TokenFee]

    @model_validator(mode="before")
    def cast(cls, values):
        fee = values["totalProtocolFeePaidInBPT"]
        values["totalProtocolFeePaidInBPT"] = Decimal(fee) if fee else Decimal(0)
        return values
