from web3 import Web3
from typing import Union, List, Dict
import json
import os
from importlib.resources import files


### These functions are to deal with differing web3 versions and the need to use 5.x for legacy brownie code
def to_checksum_address(address: str):
    if hasattr(Web3, "toChecksumAddress"):
        return Web3.toChecksumAddress(address)
    if hasattr(Web3, "to_checksum_address"):
        return Web3.to_checksum_address(address)


def is_address(address: str):
    if hasattr(Web3, "isAddress"):
        return Web3.isAddress(address)
    if hasattr(Web3, "is_address"):
        return Web3.isAddress(address)


def get_abi(contract_name: str) -> Union[Dict, List[Dict]]:
    abi_path = files(__package__).joinpath(f"abi/{contract_name}.json")
    with open(abi_path) as f:
        return json.load(f)


def flatten_nested_dict(d):
    for key, value in list(d.items()):
        if isinstance(value, dict):
            d.pop(key)
            d.update(value)
    return d
