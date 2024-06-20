from typing import Optional, List, Tuple
from decimal import Decimal
from dataclasses import dataclass, fields
from enum import Enum
from pydantic import BaseModel, validator, Field


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
    paidProtocolFees: Optional[Decimal] = Field(None, alias='paidProtocolFees')

    @validator('paidProtocolFees', pre=True, always=True)
    def cast_fees(cls, v):
        if v is None or v == '0':
            return Decimal(0)
        return Decimal(v)
    
    @validator('symbol', pre=True, always=True)
    def validate_symbol(cls, v):
        if not isinstance(v, str) or not v:
            return ''
        return v

class PoolSnapshot(BaseModel):
    timestamp: int
    protocolFee: Decimal
    swapFees: Decimal
    swapVolume: Decimal
    liquidity: Decimal
    address: str
    id: str
    symbol: str
    totalProtocolFeePaidInBPT: Decimal = Field(default=Decimal(0))
    tokens: List[TokenFee]
    
    @validator('totalProtocolFeePaidInBPT', pre=True, always=True)
    def set_default_total_fee(cls, v):
        if v is None:
            return Decimal(0)
        return Decimal(v)

    @validator('protocolFee', 'swapFees', 'swapVolume', 'liquidity', pre=True)
    def str_to_decimal(cls, v):
        return Decimal(v)

    @validator('symbol', pre=True, always=True)
    def validate_symbol(cls, v):
        if not isinstance(v, str) or not v:
            return ''
        return v