from dataclasses import dataclass
from typing import List, Optional


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
            inputs = [InputType(name=name, type=typ) for name, typ in zip(input_names, input_types)]
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
