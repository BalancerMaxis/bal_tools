from urllib.request import urlopen
import os
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from typing import Optional, Union, List, Dict
from decimal import Decimal
from bal_addresses import AddrBook
from web3 import Web3

from .utils import get_abi
from .models import *


graphql_base_path = f"{os.path.dirname(os.path.abspath(__file__))}/graphql"

AURA_SUBGRAPHS_BY_CHAIN = {
    "mainnet": "https://graph.data.aura.finance/subgraphs/name/aura/aura-mainnet-v2-1",
    "arbitrum": "https://api.thegraph.com/subgraphs/name/aurafinance/aura-finance-arbitrum",
    "optimism": "https://api.thegraph.com/subgraphs/name/aurafinance/aura-finance-optimism",
    "gnosis": "https://api.thegraph.com/subgraphs/name/aurafinance/aura-finance-gnosis-chain",
    "base": "https://api.thegraph.com/subgraphs/name/aurafinance/aura-finance-base",
    "polygon": "https://api.thegraph.com/subgraphs/name/aurafinance/aura-finance-polygon",
    "zkevm": "https://api.studio.thegraph.com/query/69982/aura-finance-zkevm/version/latest",
    "avalanche": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-avalanche/version/v0.0.1/api",
}


class Subgraph:
    V3_URL = "https://api-v3.balancer.fi"

    def __init__(self, chain: str = "mainnet"):
        chain = chain.lower()
        if chain not in AddrBook.chain_ids_by_name.keys():
            raise ValueError(f"Invalid chain: {chain}")
        self.chain = chain

    def get_subgraph_url(self, subgraph="core") -> str:
        """
        perform some soup magic to determine the latest subgraph url used in the official frontend

        params:
        - subgraph: "core", "gauges" , "blocks" or "aura"

        returns:
        - https url of the subgraph
        """
        chain = "gnosis-chain" if self.chain == "gnosis" else self.chain
        
        # TODO: remove this once the frontend is updated
        if chain == "polygon" and subgraph == "core":
            return "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-polygon-v2"

        if subgraph == "core":
            magic_word = "subgraph:"
        elif subgraph == "gauges":
            magic_word = "gauge:"
        elif subgraph == "blocks":
            magic_word = "blocks:"
            ## UI has no blocks subgraph for op
            if chain == "optimism":
                return "https://api.thegraph.com/subgraphs/name/iliaazhel/optimism-blocklytics"
        elif subgraph == "aura":
            return AURA_SUBGRAPHS_BY_CHAIN.get(chain, None)

        # get subgraph url from production frontend
        frontend_file = f"https://raw.githubusercontent.com/balancer/frontend-v2/develop/src/lib/config/{chain}/index.ts"
        found_magic_word = False
        with urlopen(frontend_file) as f:
            for line in f:
                if found_magic_word:
                    url = line.decode("utf-8").strip().strip(" ,'")
                    return url
                if magic_word + " " in str(line):
                    # url is on same line
                    return line.decode("utf-8").split(magic_word)[1].strip().strip(",'")
                if magic_word in str(line):
                    # url is on next line, return it on the next iteration
                    found_magic_word = True

    def fetch_graphql_data(self, subgraph, query, params: dict = None, url: str = None):
        """
        query a subgraph using a locally saved query

        params:
        - query: the name of the query (file) to be executed
        - params: optional parameters to be passed to the query

        returns:
        - result of the query
        """
        # build the client
        if not url:
            url = self.get_subgraph_url(subgraph)

        transport = RequestsHTTPTransport(
            url=url,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        # retrieve the query from its file and execute it
        with open(f"{graphql_base_path}/{subgraph}/{query}.gql") as f:
            gql_query = gql(f.read())
        result = client.execute(gql_query, variable_values=params)

        return result

    def get_first_block_after_utc_timestamp(self, timestamp: int) -> int:
        data = self.fetch_graphql_data(
            "blocks", "first_block_after_ts", {"timestamp": int(timestamp)}
        )
        return int(data["blocks"][0]["number"])

    def get_twap_price_token(
        self, addresses: Union[List[str], str], chain: GqlChain, date_range: DateRange
    ) -> Union[TWAPResult, List[TWAPResult]]:
        """
        fetches historical token prices and calculates the TWAP over the given date range.

        :param addresses: list of token addresses or a single address.
        :param chain: chain network from GqlChain enum.
        :param date_range: tuple of (start_date_ts, end_date_ts).
        :return: TWAPResult(s).
        """
        if isinstance(addresses, str):
            addresses = [addresses]

        start_date_ts, end_date_ts = date_range[0], date_range[1]
        if end_date_ts - start_date_ts > 90 * 24 * 3600:
            raise ValueError("Date range should be 90 days or less.")

        chain = chain.value if isinstance(chain, GqlChain) else chain
        params = {"addresses": addresses, "chain": chain, "range": "NINETY_DAY"}

        token_data = self.fetch_graphql_data(
            "core",
            "get_historical_token_prices",
            params,
            url=self.V3_URL,
        )

        def calc_twap(address: str) -> TWAPResult:
            prices = [
                Decimal(item["price"])
                for entry in token_data["tokenGetHistoricalPrices"]
                if entry["address"].lower() == address.lower()
                and entry["chain"].lower() == chain.lower()
                for item in entry["prices"]
                if end_date_ts >= int(item["timestamp"]) >= start_date_ts
            ]
            if not prices:
                return None
            return TWAPResult(address=address, twap=sum(prices) / len(prices))

        results = [calc_twap(addr) for addr in addresses]
        return results[0] if len(results) == 1 else results

    def get_twap_price_bpt(
        self, pool_id: str, chain: GqlChain, date_range: DateRange
    ) -> Decimal:
        """
        fetches the TWAP price of a pool's BPT over the given date range.

        params:
        - pool_id: the id of the pool
        - chain: the chain network from GqlChain enum
        - date_range: tuple of (start_date_ts, end_date_ts)

        returns:
        - Decimal(twap)
        """
        chain =  chain.value if isinstance(chain, GqlChain) else chain
        params = {
            "chain": chain,
            "id": pool_id,
        }

        token_data = self.fetch_graphql_data(
            "core",
            "get_pool_tokens",
            params,
            url=self.V3_URL,
        )["poolGetPool"]

        bpt_supply = Decimal(token_data["dynamicData"]["totalShares"])
        token_addresses = [token["address"] for token in token_data["poolTokens"]]

        twap_results = self.get_twap_price_token(
            addresses=token_addresses,
            chain=chain,
            date_range=date_range,
        )

        pool_value = Decimal(0)
        for token, twap_result in zip(token_data["poolTokens"], twap_results):
            balance = Decimal(token["balance"])
            pool_value += twap_result["twap"] * balance

        return pool_value / bpt_supply

    def calculate_aura_vebal_share(self, web3: Web3, block_number: int) -> Decimal:
        """
        Function that calculate veBAL share of AURA auraBAL from the total supply of veBAL
        """
        ve_bal_contract = web3.eth.contract(
            address=web3.to_checksum_address(
                "0xC128a9954e6c874eA3d62ce62B468bA073093F25"
            ),
            abi=get_abi("ERC20"),
        )
        total_supply = ve_bal_contract.functions.totalSupply().call(
            block_identifier=block_number
        )
        aura_vebal_balance = ve_bal_contract.functions.balanceOf(
            "0xaF52695E1bB01A16D33D7194C28C42b10e0Dbec2"  # veBAL aura holder
        ).call(block_identifier=block_number)
        return Decimal(aura_vebal_balance) / Decimal(total_supply)

    def fetch_all_pools_info(self) -> List[Pool]:
        """
        Fetches all pools info from balancer graphql api
        """
        res = self.fetch_graphql_data(
            "core", "vebal_get_voting_list", url=self.V3_URL
        )
        return [Pool(**pool) for pool in res["veBalGetVotingList"]]

    def get_balancer_pool_snapshots(
        self, block: int
    ) -> List[PoolSnapshot]:
        all_pools = []
        limit = 1000
        offset = 0
        while True:
            result = self.fetch_graphql_data(
                "core",
                "pool_snapshots",
                {"first": limit, "skip": offset, "block": block},
            )
            all_pools.extend([PoolSnapshot(**pool) for pool in result["poolSnapshots"]])
            offset += limit
            if offset >= 5000:
                break
            if len(result["poolSnapshots"]) < limit - 1:
                break
        return all_pools
