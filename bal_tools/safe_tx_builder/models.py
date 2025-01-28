from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Meta(BaseModel):
    name: str = Field(default="Transactions Batch")
    description: str = Field(default="")
    txBuilderVersion: str = Field(default="1.16.3")
    createdFromSafeAddress: str = Field(default="")
    createdFromOwnerAddress: str = Field(default="")
    checksum: str = Field(
        default="0x0000000000000000000000000000000000000000000000000000000000000000"
    )


class InputType(BaseModel):
    name: str = Field(default="")
    type: str = Field(default="")
    internalType: str = Field(default="")


class ContractMethod(BaseModel):
    inputs: List[InputType] = Field(default_factory=list)
    name: str = Field(default="")
    payable: bool = Field(default=False)


class Transaction(BaseModel):
    to: str = Field(default="")
    value: str = Field(default="0")
    data: Optional[str] = Field(default=None)
    contractMethod: ContractMethod = Field(default_factory=ContractMethod)
    contractInputsValues: Dict[str, Any] = Field(default_factory=dict)


class BasePayload(BaseModel):
    version: str = Field(default="1.0")
    chainId: str = Field(default="1")
    createdAt: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    meta: Meta = Field(default_factory=Meta)
    transactions: List[Transaction] = Field(default_factory=list)


class TemplateType(Enum):
    BASE = ("base.json", BasePayload)
    TRANSACTION = ("tx.json", Transaction)
    INPUT_TYPE = ("input_type.json", InputType)

    @property
    def file_name(self):
        return self.value[0]

    @property
    def model(self):
        return self.value[1]
