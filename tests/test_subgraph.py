import pytest
from datetime import datetime
from decimal import Decimal

from bal_tools.subgraph import Subgraph, GqlChain, Pool, PoolSnapshot, DateRange


@pytest.fixture(scope="module")
def date_range():
    now = int(datetime.utcnow().timestamp())
    two_weeks_ago = now - (60 * 60 * 24 * 7 * 1)
    return (two_weeks_ago, now)


def test_get_first_block_after_utc_timestamp(chain, subgraph_all_chains):
    """
    confirm we get the correct block number back
    """
    if chain == "mainnet":
        block = subgraph_all_chains.get_first_block_after_utc_timestamp(1708607101)
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


def test_get_twap_price_token(subgraph, date_range):
    res = subgraph.get_twap_price_token(
        addresses=["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"],
        chain=GqlChain.MAINNET,
        date_range=date_range,
    )
    assert res["address"] == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    assert isinstance(res["twap"], Decimal)


def test_get_twap_price_bpt(subgraph, date_range):
    res = subgraph.get_twap_price_bpt(
        pool_id="0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014",
        chain=GqlChain.MAINNET,
        date_range=date_range,
    )
    assert isinstance(res, Decimal)


def test_fetch_all_pools_info(subgraph):
    res = subgraph.fetch_all_pools_info()
    assert isinstance(res[0], Pool)


def test_get_balancer_pool_snapshots(subgraph, pool_snapshot_apis):
    for url, block in pool_snapshot_apis.items():
        res = subgraph.get_balancer_pool_snapshots(block, url)
        assert isinstance(res[0], PoolSnapshot)
