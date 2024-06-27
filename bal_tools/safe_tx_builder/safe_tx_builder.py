from typing import Optional, Union
from datetime import datetime, timezone
import os

from bal_addresses import AddrBook
from web3 import Web3

from .models import *


class SafeTxBuilder:
    _instance = None

    def __new__(
        cls,
        safe_address: Optional[str] = None,
        chain_id: str = "1",
        version: str = "1.0",
        timestamp: Optional[str] = None,
        tx_builder_version: str = "1.16.3",
    ):
        if cls._instance is None:
            if safe_address is None:
                raise ValueError("`safe_address` is required")
            cls._instance = super(SafeTxBuilder, cls).__new__(cls)
            cls._instance._initialize(
                safe_address, chain_id, version, timestamp, tx_builder_version
            )
        return cls._instance

    def _initialize(
        self,
        safe_address: str,
        chain_id: str,
        version: str,
        timestamp: Optional[str],
        tx_builder_version: str,
    ):
        self.chain_id = chain_id
        self.addr_book = AddrBook(AddrBook.chain_names_by_id[int(self.chain_id)]).flatbook
        self.safe_address = self._resolve_address(safe_address)
        self.version = version
        self.timestamp = timestamp if timestamp else datetime.now(timezone.utc)
        self.tx_builder_version = tx_builder_version
        self.base_payload = self.load_template(TemplateType.BASE)
        self._load_payload_metadata()

    @staticmethod
    def load_template(
        template_type: TemplateType,
    ) -> Union[BasePayload, Transaction, InputType]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "templates", template_type.file_name)

        model = template_type.model
        with open(file_path, "r") as f:
            file_content = f.read()

        return model.model_validate_json(file_content)

    def _resolve_address(self, identifier: str) -> str:
        if Web3.is_address(identifier):
            return identifier

        return self.addr_book[identifier]

    def _load_payload_metadata(self):
        self.base_payload.version = self.version
        self.base_payload.chainId = self.chain_id
        self.base_payload.createdAt = int(self.timestamp.timestamp())
        self.base_payload.meta.txBuilderVersion = self.tx_builder_version
        self.base_payload.meta.createdFromSafeAddress = self.safe_address

    def output_payload(self, output_file: str) -> BasePayload:
        """
        output the final json payload to `output_file`
        returns the payload
        """
        with open(output_file, "w") as f:
            f.write(self.base_payload.model_dump_json())

        return self.base_payload
