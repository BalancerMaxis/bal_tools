import pytest
import json

from bal_addresses import AddrBook
from bal_tools.pools_gauges import BalPoolsGauges
from bal_tools.subgraph import Subgraph
from bal_tools.ecosystem import Aura
from bal_tools.safe_tx_builder import SafeTxBuilder


@pytest.fixture(scope="module", params=list(AddrBook.chains["CHAIN_IDS_BY_NAME"]))
def chain(request):
    chain = request.param
    return chain


@pytest.fixture(scope="module")
def bal_pools_gauges(chain):
    return BalPoolsGauges(chain)


@pytest.fixture(scope="module")
def subgraph(chain):
    return Subgraph(chain)


@pytest.fixture(scope="module")
def aura(chain):
    return Aura(chain)

@pytest.fixture(scope="module")
def msig_address():
    return "0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f"

@pytest.fixture(scope="module")
def safe_tx_builder(msig_address) -> SafeTxBuilder:
    return SafeTxBuilder(msig_address)

@pytest.fixture(scope="module")
def erc20_abi():
    with open("tests/abi/erc20.json", "r") as file:
        return json.load(file)
    
@pytest.fixture(scope="module")
def bribe_market_abi():
    with open("tests/abi/bribe_market.json", "r") as file:
        return json.load(file)
