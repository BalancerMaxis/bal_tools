import pytest

from bal_addresses import AddrBook
from bal_tools.pools_gauges import BalPoolsGauges
from bal_tools.subgraph import Subgraph
from bal_tools.ecosystem import Aura


@pytest.fixture(scope="module", params=list(AddrBook.chains["CHAIN_IDS_BY_NAME"]))
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
def pool_snapshot_blocks():
    return {
    "arbitrum": 200000000,
    "mainnet": 17000000,
    "polygon": 44000000,
    "gnosis": 28000000,
    "base": 14000000,
    "avalanche": 30000000,
    "zkevm": 1200000
}


