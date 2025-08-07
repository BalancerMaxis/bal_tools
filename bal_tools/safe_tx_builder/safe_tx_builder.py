from typing import Optional, Union
from datetime import datetime, timezone
import os

from .models import *
from ..utils import is_address, chain_ids_by_name


class SafeTxBuilder:
    _instance = None
    _last_config = None

    def __new__(
        cls,
        safe_address: Optional[str] = None,
        chain_name: str = "mainnet",
        version: str = "1.0",
        timestamp: Optional[str] = None,
        tx_builder_version: str = "1.16.3",
    ):
        if cls._instance is None:
            cls._instance = super(SafeTxBuilder, cls).__new__(cls)
            cls._instance._initialized = False

        if safe_address is not None or cls._last_config is None:
            cls._last_config = {
                "safe_address": safe_address,
                "chain_name": chain_name,
                "version": version,
                "timestamp": timestamp,
                "tx_builder_version": tx_builder_version,
            }
            cls._instance._initialize(**cls._last_config)

        return cls._instance

    def _initialize(
        self,
        safe_address: Optional[str],
        chain_name: str,
        version: str,
        timestamp: Optional[str],
        tx_builder_version: str,
    ):
        self.chain_name = chain_name
        self.chain_id = str(chain_ids_by_name()[chain_name])
        self.safe_address = safe_address
        self.version = version
        self.timestamp = timestamp if timestamp else datetime.now(timezone.utc)
        self.tx_builder_version = tx_builder_version
        self.base_payload = self.load_template(TemplateType.BASE)
        self._load_payload_metadata()
        self._initialized = True

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
            f.write(self.base_payload.model_dump_json(indent=2, exclude_none=True))

        return self.base_payload
