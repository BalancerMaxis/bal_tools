import pytest
from decimal import Decimal

from bal_tools.subgraph import (
    Subgraph,
    GqlChain,
    Pool,
    PoolSnapshot,
    DateRange,
)


@pytest.fixture(scope="module")
def date_range():
    return (1717632000, 1718015100)


@pytest.mark.skip
def test_get_first_block_after_utc_timestamp(chain, subgraph_all_chains):
    """
    currently not applicable as block api is not deterministic
    """
    # TODO: current subgraph is borked! doesnt have blocks before 20020000
    pytest.skip(f"Skipping {chain}")
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
    assert isinstance(res.twap_price, Decimal)
    assert pytest.approx(res.twap_price, rel=Decimal(1e-2)) == Decimal(3743.80)


def test_get_twap_prices(subgraph, date_range):
    prices = subgraph.get_twap_price_pool(
        pool_id="0x05ff47afada98a98982113758878f9a8b9fdda0a000000000000000000000645",
        chain=GqlChain.MAINNET,
        date_range=date_range,
    )
    assert isinstance(prices.bpt_price, Decimal)
    assert pytest.approx(prices.bpt_price, rel=Decimal(1e-2)) == Decimal(4149.46)
    assert all(isinstance(price.twap_price, Decimal) for price in prices.token_prices)


def test_get_twap_prices_custom_price_logic(subgraph, date_range, web3):
    prices = subgraph.get_twap_price_pool(
        pool_id="0x38fe2b73612527eff3c5ac3bf2dcb73784ad927400000000000000000000068c",
        chain=GqlChain.MAINNET,
        date_range=date_range,
        web3=web3,
        block=20059322,
    )
    assert isinstance(prices.bpt_price, Decimal)
    assert pytest.approx(prices.bpt_price, rel=Decimal(1e-2)) == Decimal(3707.99)
    assert all(isinstance(price.twap_price, Decimal) for price in prices.token_prices)


def test_fetch_all_pools_info(subgraph):
    res = subgraph.fetch_all_pools_info()
    assert isinstance(res[0], Pool)


def test_get_balancer_pool_snapshots(chain, subgraph_all_chains, pool_snapshot_blocks):
    if chain in pool_snapshot_blocks.keys():
        block = pool_snapshot_blocks[chain]
        res = subgraph_all_chains.get_balancer_pool_snapshots(
            block, pools_per_req=25, limit=25
        )

        assert isinstance(res[0], PoolSnapshot)
        assert all(isinstance(pool.totalProtocolFeePaidInBPT, Decimal) for pool in res)
        assert all(isinstance(pool.tokens[0].paidProtocolFees, Decimal) for pool in res)
