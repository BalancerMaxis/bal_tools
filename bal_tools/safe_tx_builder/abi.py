from dataclasses import dataclass
from typing import List, Optional, Any
from eth_abi import encode, decode
from eth_utils import function_signature_to_4byte_selector


@dataclass
class InputType:
    name: str
    type: str


@dataclass
class ABIFunction:
    name: Optional[str] = None
    inputs: Optional[List[InputType]] = None
    outputs: List[str] = None
    constant: bool = False
    payable: bool = False
    
    @staticmethod
    def func_selector(sig: str) -> bytes:
        return function_signature_to_4byte_selector(sig)

    def get_selector(self) -> bytes:
        return self.func_selector(self.get_signature())

    def get_signature(self) -> str:
        if self.name is None:
            raise ValueError("Cannot compute signature without a name")

        input_types = ""
        if self.inputs:
            input_types = ",".join([input.type for input in self.inputs])

        return f"{self.name}({input_types})"

    def encode_inputs(self, values: List[Any]) -> bytes:
        selector = self.get_selector()
        if self.inputs == []:
            return selector
        encoded_inputs = encode([input.type for input in self.inputs], values)
        return selector + encoded_inputs


@dataclass
class ContractABI:
    functions: List[ABIFunction]
    name: Optional[str] = None


def parse_json_abi(abi: dict) -> ContractABI:
    functions = []
    for entry in abi:
        if entry["type"] == "function":
            name = entry["name"]
            input_types = [collapse_if_tuple(inputs) for inputs in entry["inputs"]]
            input_names = [i["name"] for i in entry["inputs"]]
            inputs = [
                InputType(name=name, type=typ)
                for name, typ in zip(input_names, input_types)
            ]
            outputs = [collapse_if_tuple(outputs) for outputs in entry["outputs"]]
            constant = entry["stateMutability"] in ("view", "pure")
            payable = entry["stateMutability"] == "payable"
            functions.append(
                ABIFunction(
                    name=name,
                    inputs=inputs,
                    outputs=outputs,
                    constant=constant,
                    payable=payable,
                )
            )
    return ContractABI(functions)


def collapse_if_tuple(abi: dict) -> str:
    typ = abi["type"]
    if not typ.startswith("tuple"):
        return typ

    delimited = ",".join(collapse_if_tuple(c) for c in abi["components"])
    # Whatever comes after "tuple" is the array dims.  The ABI spec states that
    # this will have the form "", "[]", or "[k]".
    array_dim = typ[5:]
    collapsed = "({}){}".format(delimited, array_dim)

    return collapsed
