import pytest

from bal_tools.subgraph import Subgraph


def test_get_first_block_after_utc_timestamp(chain, subgraph):
    """
    confirm we get the correct block number back
    """
    # TODO: current subgraph is borked! doesnt have blocks before 20020000
    pytest.skip(f"Skipping {chain}")
    if chain == "mainnet":
        block = subgraph.get_first_block_after_utc_timestamp(1708607101)
        assert isinstance(block, int)
        assert block == 19283331
    else:
        pytest.skip(f"Skipping {chain}")


def test_invalid_chain():
    """
    we should get a raise when passing an invalid chain
    """

    with pytest.raises(ValueError):
        Subgraph("invalid_chain")
