from typing import Dict, List
import requests
from .utils import to_checksum_address, flatten_nested_dict

from gql.transport.exceptions import TransportQueryError
from bal_tools.subgraph import Subgraph
from bal_tools.errors import NoResultError
from bal_tools.models import PoolData, GaugePoolData, GaugeData, CorePools, PoolId, Symbol

GITHUB_RAW_OUTPUTS = (
    "https://raw.githubusercontent.com/BalancerMaxis/bal_addresses/main/outputs"
)
GITHUB_RAW_CONFIG = (
    "https://raw.githubusercontent.com/BalancerMaxis/bal_addresses/main/config"
)


class BalPoolsGauges:
    def __init__(self, chain="mainnet", use_cached_core_pools=True):
        self.chain = chain.lower()
        self.subgraph = Subgraph(self.chain)
        self.vebal_voting_list = self.subgraph.fetch_graphql_data(
            "apiv3", "vebal_get_voting_list"
        )["veBalGetVotingList"]
        if use_cached_core_pools:
            core_pools_data = requests.get(f"{GITHUB_RAW_OUTPUTS}/core_pools.json").json()
            self.core_pools = CorePools(pools=core_pools_data.get(self.chain, {}))
        else:
            self.core_pools = self.build_core_pools()

    def is_pool_exempt_from_yield_fee(self, pool_id: str) -> bool:
        data = self.subgraph.fetch_graphql_data(
            "core", "yield_fee_exempt", {"poolId": pool_id}
        )
        for pool in data["poolTokens"]:
            address = pool["poolId"]["address"]
            if pool["id"].split("-")[-1] == address:
                continue
            if pool["isExemptFromYieldProtocolFee"] == True:
                return True

    def is_pool_on_vebal_list(self, pool_id: str) -> bool:
        for pool in self.vebal_voting_list:
            if pool["id"] == pool_id:
                if not pool["gauge"]["isKilled"]:
                    return True
        return False

    def get_bpt_balances(self, pool_id: str, block: int) -> Dict[str, int]:
        variables = {"poolId": pool_id, "block": int(block)}
        data = self.subgraph.fetch_graphql_data(
            "core", "get_user_pool_balances", variables
        )
        results = {}
        if "pool" in data and data["pool"]:
            for share in data["pool"]["shares"]:
                user_address = to_checksum_address(share["userAddress"]["id"])
                results[user_address] = float(share["balance"])
        return results

    def get_gauge_deposit_shares(self, gauge_address: str, block: int) -> Dict[str, int]:
        gauge_address = to_checksum_address(gauge_address)
        variables = {"gaugeAddress": gauge_address, "block": int(block)}
        data = self.subgraph.fetch_graphql_data("gauges", "fetch_gauge_shares", variables)
        results = {}
        if "gaugeShares" in data:
            for share in data["gaugeShares"]:
                user_address = to_checksum_address(share["user"]["id"])
                results[user_address] = float(share["balance"])
        return results

    def get_preferential_gauge(self, pool_id: str) -> bool:
        try:
            return to_checksum_address(self.subgraph.fetch_graphql_data(
                "apiv3", "get_pool_preferential_gauge", {"chain": self.chain.upper(), "poolId": pool_id}
            )["poolGetPool"]["staking"]["gauge"]["gaugeAddress"])
        except:
            return None

    def is_core_pool(self, pool_id: str) -> bool:
        """
        check if a pool is a core pool using a fresh query to the subgraph

        params:
        pool_id: this is the long version of a pool id, so contract address + suffix

        returns:
        True if the pool is a core pool
        """
        return pool_id in self.core_pools.pools

    def query_preferential_gauges(self, skip=0, step_size=100) -> list:
        """
        TODO: add docstring
        """
        variables = {"skip": skip, "step_size": step_size}
        data = self.subgraph.fetch_graphql_data("gauges", "pref_gauges", variables)
        try:
            result = data["liquidityGauges"]
        except KeyError:
            result = []
        if len(result) > 0:
            # didnt reach end of results yet, collect next page
            result += self.query_preferential_gauges(skip + step_size, step_size)
        return result

    def query_root_gauges(self, skip=0, step_size=100) -> list:
        variables = {"skip": skip, "step_size": step_size}
        data = self.subgraph.fetch_graphql_data("gauges", "root_gauges", variables)
        try:
            result = data["rootGauges"]
        except KeyError:
            result = []
        if len(result) > 0:
            # didnt reach end of results yet, collect next page
            result += self.query_root_gauges(skip + step_size, step_size)
        return result

    def query_all_gauges(self, include_other_gauges=True) -> List[GaugeData]:
        """
        query all gauges from the apiv3 subgraph
        """
        def paginate_all_gauges_query(skip=0, step_size=100):
            variables = {"chain": self.chain.upper(), "skip": skip, "step_size": step_size}
            data = self.subgraph.fetch_graphql_data("apiv3", "get_gauges", variables)

            try:
                result = data["poolGetPools"]
            except KeyError:
                result = []
            if len(result) > 0:
                # didnt reach end of results yet, collect next page
                result += paginate_all_gauges_query(skip + step_size, step_size)
            return result

        all_gauges = []
        for pool in paginate_all_gauges_query():
            gauge_pool = GaugePoolData(**flatten_nested_dict(pool))
            if gauge_pool.staking is not None and gauge_pool.staking.get('gauge') is not None:
                gauge = gauge_pool.staking['gauge']
                all_gauges.append(GaugeData(
                    address=gauge['gaugeAddress'],
                    symbol=f"{gauge_pool.symbol}-gauge"
                ))
                if include_other_gauges:
                    for other_gauge in gauge.get('otherGauges', []):
                        all_gauges.append(GaugeData(
                            address=other_gauge['id'],
                            symbol=f"{gauge_pool.symbol}-gauge"
                        ))
        return all_gauges

    def query_all_pools(self) -> List[PoolData]:
        """
        query all pools from the apiv3 subgraph
        filters out disabled pools
        """
        def paginate_all_pools_query(skip=0, step_size=100):
            variables = {"chain": self.chain.upper(), "skip": skip, "step_size": step_size}
            data = self.subgraph.fetch_graphql_data("apiv3", "get_pools", variables)

            try:
                result = data["poolGetPools"]
            except KeyError:
                result = []
            if len(result) > 0:
                # didnt reach end of results yet, collect next page
                result += paginate_all_pools_query(skip + step_size, step_size)
            return result

        all_pools = []
        for pool in paginate_all_pools_query():
            pool_data = PoolData(**flatten_nested_dict(pool))
            if pool_data.dynamicData['swapEnabled']:
                all_pools.append(pool_data)
        return all_pools

    def get_last_join_exit(self, pool_id: int) -> int:
        """
        Returns a timestamp of the last join/exit for a given pool id
        """
        data = self.subgraph.fetch_graphql_data(
            "core", "last_join_exit", {"poolId": pool_id}
        )
        try:
            return data["joinExits"][0]["timestamp"]
        except:
            raise NoResultError(
                "empty or malformed results looking for last join/exit on"
                f" pool {self.chain}:{pool_id}"
            )

    def get_pool_tvl(self, pool_id: str) -> float:
        """
        Returns the TVL of a pool as per the API V3 subgraph
        """
        try:
            data = self.subgraph.fetch_graphql_data(
                "apiv3", "get_pool_tvl", {"chain": self.chain.upper(), "poolId": pool_id}
            )
        except TransportQueryError:
            return 0
        try:
            return float(data["poolGetPool"]["dynamicData"]["totalLiquidity"])
        except:
            raise NoResultError(
                "empty or malformed results looking for TVL of"
                f" pool {self.chain}:{pool_id}"
            )

    def get_liquid_pools_with_protocol_yield_fee(self) -> dict:
        """
        query the official balancer subgraph and retrieve pools that
        meet all three of the following conditions:
        - have at least one underlying asset that is yield bearing
        - have a liquidity greater than $100k
        - provide the protocol with a fee on the yield; by either:
          - having a yield fee > 0
          - being a meta stable pool with swap fee > 0 (these old style pools dont have
            the yield fee field yet)
          - being a gyro pool (take yield fee by default in case of a rate provider)

        returns:
        dictionary of the format {pool_id: symbol}
        """
        filtered_pools = {}
        data = self.subgraph.fetch_graphql_data("core", "liquid_pools_protocol_yield_fee")
        try:
            for pool in data["pools"]:
                if self.get_pool_tvl(pool["id"]) >= 100_000:
                    filtered_pools[pool["id"]] = pool["symbol"]
        except KeyError:
            # no results for this chain
            pass
        return filtered_pools

    def has_alive_preferential_gauge(self, pool_id: str) -> bool:
        """
        check if a pool has an alive preferential gauge using a fresh query to the subgraph

        params:
        - pool_id: id of the pool

        returns:
        - True if the pool has a preferential gauge which is not killed
        """
        variables = {"pool_id": pool_id}
        data = self.subgraph.fetch_graphql_data(
            "gauges", "alive_preferential_gauge", variables
        )
        try:
            result = data["pools"]
        except KeyError:
            result = []
        if len(result) == 0:
            print(f"Pool {pool_id} on {self.chain} has no preferential gauge")
            return False
        for gauge in result:
            if gauge["preferentialGauge"]["isKilled"] == False:
                return True
        print(f"Pool {pool_id} on {self.chain} has no alive preferential gauge")

    def build_core_pools(self) -> CorePools:
        """
        build the core pools dictionary by taking pools from `get_pools_with_rate_provider` and:
        - confirm the pool has an active gauge on the vebal voting list
        - check if the pool has an alive preferential gauge
        - add pools from whitelist
        - remove pools from blacklist

        returns:
        CorePools object containing the core pools for the current chain
        """
        core_pools = self.get_liquid_pools_with_protocol_yield_fee()

        for pool_id in core_pools.copy():
            # confirm the pool has an active gauge on the vebal voting list
            if not self.is_pool_on_vebal_list(pool_id):
                del core_pools[pool_id]
                continue
            # make sure the pools have an alive preferential gauge
            if not self.has_alive_preferential_gauge(pool_id):
                del core_pools[pool_id]
                continue
            # exclude pools with yield fee exemption
            elif self.is_pool_exempt_from_yield_fee(pool_id):
                del core_pools[pool_id]

        # add pools from whitelist
        whitelist = requests.get(f"{GITHUB_RAW_CONFIG}/core_pools_whitelist.json")
        whitelist.raise_for_status()
        whitelist = whitelist.json()
        try:
            for pool, symbol in whitelist[self.chain].items():
                if pool not in core_pools:
                    core_pools[pool] = symbol
        except KeyError:
            # no results for this chain
            pass

        # remove pools from blacklist
        blacklist = requests.get(f"{GITHUB_RAW_CONFIG}/core_pools_blacklist.json")
        blacklist.raise_for_status()
        blacklist = blacklist.json()
        try:
            for pool in blacklist[self.chain]:
                if pool in core_pools:
                    del core_pools[pool]
        except KeyError:
            # no results for this chain
            pass

        return CorePools(pools={PoolId(k): Symbol(v) for k, v in core_pools.items()})
