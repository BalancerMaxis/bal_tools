import json

from .safe_tx_builder import SafeTxBuilder
from .abi import ABIFunction, ContractABI, parse_json_abi
from .models import *


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class SafeContract:
    def __init__(
        self,
        address: str,
        abi: dict = None,
        abi_file_path: str = None,
    ):
        self.tx_builder = SafeTxBuilder()
        if not self.tx_builder._initialized:
            raise RuntimeError(
                "SafeTxBuilder must be initialized before using SafeContract"
            )
        self.address = address
        self.abi = self._load_abi(abi, abi_file_path)

    def __getattr__(self, attribute):
        if self.abi and hasattr(self.abi, "functions"):
            funcs_found = [f for f in self.abi.functions if f.name == attribute]
            n_found = len(funcs_found)

            if n_found == 1:
                return lambda *args, **kwargs: self.call_function(
                    funcs_found[0], args, kwargs
                )
            elif n_found > 1:
                return lambda *args, **kwargs: self.call_function(
                    next(f for f in funcs_found if len(f.inputs) == len(args)),
                    args,
                    kwargs,
                )

        raise AttributeError(f"No function named {attribute} in contract ABI")

    def _load_abi(self, abi: dict = None, file_path: dict = None) -> ContractABI:
        if not abi and not file_path:
            raise ValueError("Either `abi` or `abi_file_path` must be provided")

        if file_path:
            with open(file_path, "r") as file:
                abi = json.load(file)

        return parse_json_abi(abi)

    def _handle_type(self, value):
        try:
            if isinstance(value, float):
                value = int(value)
            return str(value)
        except Exception as e:
            raise ValueError(f"Failed to convert value to string: {e}")

    def _convert_components_to_inputtype(self, components):
        result = []
        for comp in components:
            input_type = self.tx_builder.load_template(TemplateType.INPUT_TYPE)
            input_type.name = comp.name
            input_type.type = comp.type
            input_type.internalType = comp.internalType or comp.type
            
            # Recursively handle nested components
            if hasattr(comp, 'components') and comp.components:
                input_type.components = self._convert_components_to_inputtype(comp.components)
            
            result.append(input_type)
        return result

    def call_function(self, func: ABIFunction, args: tuple, kwargs: dict = {}):
        if func.constant:
            raise ValueError("Cannot build a tx for a constant function")

        if len(args) != len(func.inputs):
            raise ValueError("Number of arguments does not match function inputs")

        tx = self.tx_builder.load_template(TemplateType.TRANSACTION)
        tx.to = self.address
        tx.contractMethod.name = func.name
        tx.contractMethod.payable = func.payable
        tx.value = str(kwargs.get("value", "0"))

        if not func.inputs:
            tx.contractInputsValues = None  # type: ignore

        for arg, input_type in zip(args, func.inputs):
            input_template = self.tx_builder.load_template(TemplateType.INPUT_TYPE)
            input_template.name = input_type.name
            input_template.type = input_type.type
            input_template.internalType = input_type.internalType or input_type.type
            
            if hasattr(input_type, 'components') and input_type.components:
                input_template.components = self._convert_components_to_inputtype(input_type.components)
            
            tx.contractMethod.inputs.append(input_template)
            tx.contractInputsValues[input_type.name] = self._handle_type(arg)

        self.tx_builder.base_payload.transactions.append(tx)
