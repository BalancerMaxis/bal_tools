from typing import Optional, Union
from datetime import datetime
import os

from .models import *

class SafeTxBuilder:
    _instance = None
    safe_address: Optional[str] = None
    base_payload: Optional[BasePayload] = None
    chain_id: str = "1"
    version: str = "1.0"
    timestamp: str
    tx_builder_version: str = "1.16.3"

    def __new__(cls, safe_address: str = None, chain_id: str = "1", version: str = "1.0", timestamp: str = None, tx_builder_version: str = "1.16.3"):
        if cls._instance is None:
            cls._instance = super(SafeTxBuilder, cls).__new__(cls)
            cls._instance.safe_address = safe_address
            cls._instance.chain_id = chain_id
            cls._instance.version = version
            cls._instance.timestamp = timestamp if timestamp else datetime.utcnow().timestamp()
            cls._instance.tx_builder_version = tx_builder_version
            cls._instance.base_payload = cls.load_template(TemplateType.BASE)
            cls._instance.add_medadata()
        else:
            if safe_address:
                cls._instance.safe_address = safe_address
                cls._instance.add_medadata()
        return cls._instance

    @staticmethod
    def load_template(template_type: TemplateType) -> Union[BasePayload, Transaction, InputType]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'templates', template_type.file_name)

        model = template_type.model
        with open(file_path, 'r') as f:
            file_content = f.read()

        return model.model_validate_json(file_content)

    def add_medadata(self):
        self.base_payload.version = self.version
        self.base_payload.chainId = self.chain_id
        self.base_payload.createdAt = int(self.timestamp)
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