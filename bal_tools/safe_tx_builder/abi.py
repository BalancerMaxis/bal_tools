from dataclasses import dataclass
from typing import List, Optional


@dataclass
class InputType:
    name: str
    type: str
    internalType: Optional[str] = None
    components: Optional[List["InputType"]] = None


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


def parse_input_type(input_desc: dict) -> InputType:
    """Parse input type preserving component structure for tuples."""
    name = input_desc.get("name", "")
    type_str = input_desc.get("type", "")
    internal_type = input_desc.get("internalType", type_str)

    # Preserve components for tuple types
    components = None
    if type_str.startswith("tuple"):
        components_raw = input_desc.get("components", [])
        # Recursively parse nested components - validate type safety
        if components_raw and isinstance(components_raw, list):
            components = [parse_input_type(comp) for comp in components_raw]

    return InputType(
        name=name, type=type_str, internalType=internal_type, components=components
    )


def parse_json_abi(abi: dict) -> ContractABI:
    functions = []
    for entry in abi:
        if entry["type"] == "function":
            name = entry["name"]
            # Parse inputs preserving structure
            inputs = [parse_input_type(inp) for inp in entry["inputs"]]
            outputs = [o.get("type", "") for o in entry["outputs"]]
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
