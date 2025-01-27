import pytest
from decimal import Decimal
import json
import warnings

from bal_tools.subgraph import Subgraph, GqlChain, Pool, PoolSnapshot
from bal_tools.errors import NoPricesFoundError


@pytest.fixture(scope="module")
def date_range():
    return (1728190800, 1729400400)


@pytest.mark.skip
def test_get_first_block_after_utc_timestamp(chain, subgraph_all_chains):
    """
    currently not applicable as block api is not deterministic
    """
    if chain == "mainnet":
        block = subgraph_all_chains.get_first_block_after_utc_timestamp(1723117347)
        assert isinstance(block, int)
        assert block == 20483622
    else:
        pytest.skip(f"Skipping {chain}")


def test_invalid_chain():
    """
    we should get a raise when passing an invalid chain
    """

    with pytest.raises(ValueError):
        Subgraph("invalid_chain")


def test_get_twap_prices(subgraph, date_range, mainnet_core_pools):
    with open(
        f"tests/price_data/pool_prices-{date_range[0]}-{date_range[1]}.json", "r"
    ) as f:
        loaded_pool_prices = json.load(f)

    for pool_id, symbol in mainnet_core_pools:
        loaded_price = loaded_pool_prices.get(symbol)
        if loaded_price:
            try:
                prices = subgraph.get_twap_price_pool(
                    pool_id=pool_id,
                    chain=GqlChain.MAINNET,
                    date_range=date_range,
                )
                assert pytest.approx(
                    prices.bpt_price.twap_price, rel=Decimal(0.01)
                ) == Decimal(loaded_price.get("bpt_price"))
                for token_price, loaded_token_price in zip(
                    prices.token_prices, loaded_price.get("token_prices")
                ):
                    assert pytest.approx(
                        token_price.twap_price, rel=Decimal(0.01)
                    ) == Decimal(loaded_token_price.get("twap_price"))
            except NoPricesFoundError:
                continue


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


@pytest.mark.parametrize("have_thegraph_key", [True, False])
@pytest.mark.parametrize("subgraph_type", ["core", "gauges", "blocks", "aura"])
def test_find_all_subgraph_urls(
    subgraph_all_chains, have_thegraph_key, subgraph_type, monkeypatch
):
    if subgraph_all_chains.chain in ["sepolia", "mode"] and subgraph_type in [
        "aura",
        "blocks",
    ]:
        pytest.skip(
            f"No {subgraph_type} subgraph exists on {subgraph_all_chains.chain}"
        )

    if not have_thegraph_key:
        monkeypatch.setenv("GRAPH_API_KEY", "")
        subgraph_all_chains.set_silence_warnings(True)

    url = subgraph_all_chains.get_subgraph_url(subgraph_type)

    assert url is not None
    assert url is not ""

    if not have_thegraph_key:
        subgraph_all_chains.set_silence_warnings(False)


def test_warning_configuration(monkeypatch):
    monkeypatch.setenv("GRAPH_API_KEY", "")

    # Should emit warning
    with pytest.warns(UserWarning):
        subgraph = Subgraph(silence_warnings=False)
        subgraph.get_subgraph_url("core")

    # Should not emit warning
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        subgraph = Subgraph(silence_warnings=True)
        subgraph.get_subgraph_url("core")
