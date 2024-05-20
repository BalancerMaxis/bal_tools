from web3 import Web3
from typing import Union, List, Dict
import json
import os


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
    project_root_dir = os.path.abspath(os.path.dirname(__file__))
    with open(f"{project_root_dir}/abi/{contract_name}.json") as f:
        return json.load(f)
