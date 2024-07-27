import pytest
from bal_tools.drpc import Web3RpcByChain, Web3Rpc
from tests.conftest import chains


def test_drpc_by_chain(DRPC_KEY):
    if not DRPC_KEY:
        pytest.skip("Skipping DRPC_KEY not set")

    w3_by_chain = Web3RpcByChain(DRPC_KEY)
    assert not w3_by_chain.keys()

    for chain in chains:
        assert w3_by_chain[chain].eth
        
    assert sorted(w3_by_chain.keys()) == sorted(chains)
