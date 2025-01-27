import pytest
from gql.transport.exceptions import TransportQueryError
from bal_tools.models import PoolData, GaugeData
from bal_tools.models import CorePools
import json


EXAMPLE_PREFERENTIAL_GAUGES = {
    "mainnet": (  # wsteTH-WETH
        "0x93d199263632a4ef4bb438f1feb99e57b4b5f0bd0000000000000000000005c2",
        "0x5C0F23A5c1be65Fa710d385814a7Fd1Bda480b1C",
    ),
    "gnosis": (  # wstETH-GNO
        "0x4683e340a8049261057d5ab1b29c8d840e75695e00020000000000000000005a",
        "0xB812249d60b80c7Cbc9398E382eD6DFDF82E23D2",
    ),
    "arbitrum": (  # RDNT-WETH
        "0x32df62dc3aed2cd6224193052ce665dc181658410002000000000000000003bd",
        "0xcf9f895296F5e1D66a7D4dcf1d92e1B435E9f999",
    ),
}
EXAMPLE_CORE_POOLS = {
    "mainnet": (  # wsteTH-WETH
        "0x93d199263632a4ef4bb438f1feb99e57b4b5f0bd0000000000000000000005c2"
    ),
    "polygon": (  # maticX-WMATIC-BPT
        "0xcd78a20c597e367a4e478a2411ceb790604d7c8f000000000000000000000c22"
    ),
    "arbitrum": (  # wstETH/rETH/sfrxETH
        "0x0c8972437a38b389ec83d1e666b69b8a4fcf8bfd00000000000000000000049e"
    ),
    "base": (  # "rETH-WETH-BPT"
        "0xc771c1a5905420daec317b154eb13e4198ba97d0000000000000000000000023"
    ),
}
EXAMPLE_YIELD_FEE_EXEMPT_TRUE = {
    "gnosis": "0xdd439304a77f54b1f7854751ac1169b279591ef7000000000000000000000064"
}


def test_has_alive_preferential_gauge(bal_pools_gauges):
    """
    confirm example alive preferential gauge can be found
    """
    try:
        example = EXAMPLE_PREFERENTIAL_GAUGES[bal_pools_gauges.chain][0]
    except KeyError:
        pytest.skip(f"Skipping {bal_pools_gauges.chain}, no example preferential gauge")

    assert bal_pools_gauges.has_alive_preferential_gauge(example)


def test_core_pools_type(bal_pools_gauges):
    """
    confirm we get a CorePools type with entries
    """
    core_pools = bal_pools_gauges.core_pools
    assert isinstance(core_pools, CorePools)


@pytest.mark.skip(reason="core pool list can change; examples may not be valid")
def test_core_pools_attr(bal_pools_gauges):
    """
    confirm example core pool is in CorePools
    """
    core_pools = bal_pools_gauges.core_pools

    try:
        example = EXAMPLE_CORE_POOLS[bal_pools_gauges.chain]
    except KeyError:
        pytest.skip(f"Skipping {bal_pools_gauges.chain}, no example core pools")

    assert example in core_pools.keys()


@pytest.mark.skip(reason="core pool list can change; examples may not be valid")
def test_is_core_pool(bal_pools_gauges):
    """
    confirm example core pool is present
    """
    try:
        example = EXAMPLE_CORE_POOLS[bal_pools_gauges.chain]
    except KeyError:
        pytest.skip(f"Skipping {bal_pools_gauges.chain}, no example core pools")

    assert bal_pools_gauges.is_core_pool(example)


def test_is_core_pool_false(bal_pools_gauges):
    """
    confirm spoofed core pool is not present
    """
    with pytest.raises(AssertionError):
        assert bal_pools_gauges.is_core_pool(
            "0x0000000000000000000000000000000000000000000000000000000000000000"
        )


def test_is_pool_exempt_from_yield_fee(bal_pools_gauges):
    """
    confirm example pool is exempt from yield fee
    """
    try:
        example = EXAMPLE_YIELD_FEE_EXEMPT_TRUE[bal_pools_gauges.chain]
    except KeyError:
        pytest.skip(
            f"Skipping {bal_pools_gauges.chain}, no example yield fee exempt pool"
        )

    assert bal_pools_gauges.is_pool_exempt_from_yield_fee(example)


def test_build_core_pools(bal_pools_gauges):
    """
    confirm core_pools can be built and is a CorePools type
    """
    try:
        assert isinstance(bal_pools_gauges.build_core_pools(), CorePools)
    except TransportQueryError as e:
        if "Too Many Requests" in str(e):
            pytest.skip(f"Skipping {bal_pools_gauges.chain}, too many requests")


def test_get_preferential_gauge(bal_pools_gauges):
    """
    confirm we can correctly determine the preferential gauge for some given pools
    """
    try:
        example = EXAMPLE_PREFERENTIAL_GAUGES[bal_pools_gauges.chain]
    except KeyError:
        pytest.skip(f"Skipping {bal_pools_gauges.chain}, no example preferential gauge")

    assert bal_pools_gauges.get_preferential_gauge(example[0]) == example[1]


def test_query_all_pools(bal_pools_gauges):
    """
    test return data of v3 AllGauges query
    """
    response = bal_pools_gauges.query_all_pools()

    if len(response) > 0:
        assert isinstance(response[0], PoolData)


def test_query_all_gauges(bal_pools_gauges):
    """
    test return data of v3 AllPools query
    """
    response = bal_pools_gauges.query_all_gauges()

    if len(response) > 0:
        assert isinstance(response[0], GaugeData)
