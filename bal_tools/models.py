from typing import Optional, List, Tuple, TypedDict
from decimal import Decimal
from dataclasses import dataclass, fields
from enum import Enum
import dacite


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


class TWAPResult(TypedDict):
    address: str
    twap: Optional[Decimal]


@dataclass
class BaseModel:
    def __init__(self, **data):
        instance = dacite.from_dict(data_class=self.__class__, data=data)
        for field_info in fields(self):
            setattr(self, field_info.name, getattr(instance, field_info.name))


@dataclass
class Token:
    address: str
    logoURI: str
    symbol: str
    weight: Optional[str]


@dataclass
class Gauge:
    address: str
    isKilled: bool
    relativeWeightCap: Optional[str]
    addedTimestamp: Optional[int]
    childGaugeAddress: Optional[str]


@dataclass
class Pool(BaseModel):
    id: str
    address: str
    chain: str
    type: str
    symbol: str
    gauge: Gauge
    tokens: List[Token]


@dataclass
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


@dataclass
class TokenFee:
    symbol: str
    address: str
    paidProtocolFees: str


@dataclass
class PoolSnapData:
    address: str
    id: str
    symbol: str
    totalProtocolFeePaidInBPT: Optional[str]
    tokens: List[TokenFee]


@dataclass
class PoolSnapshot(BaseModel):
    pool: PoolSnapData
    timestamp: int
    protocolFee: str
    swapFees: str
    swapVolume: str
    liquidity: str
