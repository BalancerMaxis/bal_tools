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
def pool_snapshot_apis():
    return {
    "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-arbitrum-v2": 200000000,
    "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-v2": 17000000,
    "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-polygon-v2": 44000000,
    "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-gnosis-chain-v2": 28000000,
    "https://api.studio.thegraph.com/query/24660/balancer-base-v2/version/latest": 14000000,
    "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-avalanche-v2": 30000000,
    "https://api.studio.thegraph.com/query/24660/balancer-polygon-zk-v2/version/latest": 1200000
}


