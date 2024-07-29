import pytest
import json
import os

from bal_addresses import AddrBook
from bal_tools.pools_gauges import BalPoolsGauges
from bal_tools.subgraph import Subgraph
from bal_tools.ecosystem import Aura
from bal_tools.safe_tx_builder import SafeTxBuilder

from web3 import Web3
from dotenv import load_dotenv


load_dotenv()

exempt_chains = ["fantom", "mode", "fraxtal", "goerli"]
chains = [
    chain
    for chain in list(AddrBook.chains["CHAIN_IDS_BY_NAME"])
    if chain not in exempt_chains
]


@pytest.fixture(scope="module")
def web3():
    return Web3(Web3.HTTPProvider(os.getenv("ETHNODEURL")))


@pytest.fixture(scope="module", params=chains)
def chain(request):
    chain = request.param
    return chain


@pytest.fixture(scope="module")
def bal_pools_gauges(chain):
    return BalPoolsGauges(chain)


@pytest.fixture(scope="module")
def subgraph_all_chains(chain):
    return Subgraph(chain)


@pytest.fixture(scope="module")
def subgraph():
    return Subgraph()


@pytest.fixture(scope="module")
def aura(chain):
    return Aura(chain)


@pytest.fixture(scope="module")
def addr_book():
    return AddrBook("mainnet").flatbook


@pytest.fixture(scope="module")
def msig_name():
    return "multisigs/vote_incentive_recycling"


@pytest.fixture(scope="module")
def safe_tx_builder(msig_name) -> SafeTxBuilder:
    return SafeTxBuilder(msig_name)


@pytest.fixture(scope="module")
def erc20_abi():
    with open("tests/abi/erc20.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def bribe_market_abi():
    with open("tests/abi/bribe_market.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def pool_snapshot_blocks():
    return {
        "arbitrum": 200000000,
        "mainnet": 17000000,
        "polygon": 44000000,
        "gnosis": 28000000,
        "base": 14000000,
        "avalanche": 30000000,
        "zkevm": 1200000,
    }
