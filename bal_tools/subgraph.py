from urllib.request import urlopen
from urllib.parse import urlparse
import os
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Union, List, Callable, Dict

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from web3 import Web3
from bal_addresses import AddrBook

from typing import Union, List, Callable, Dict
from .utils import get_abi, flatten_nested_dict
from .models import *


graphql_base_path = f"{os.path.dirname(os.path.abspath(__file__))}/graphql"

AURA_SUBGRAPHS_BY_CHAIN = {
    "mainnet": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-mainnet/api",
    "arbitrum": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-arbitrum/api",
    "optimism": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-optimism/api",
    "gnosis": (
        "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-gnosis/api"
    ),
    "base": (
        "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-base/api"
    ),
    "polygon": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-polygon/api",
    "zkevm": (
        "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-zkevm/api"
    ),
    "avalanche": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-avalanche/api",
}


class Subgraph:
    def __init__(self, chain: str = "mainnet"):
        if chain not in AddrBook.chain_ids_by_name.keys():
            raise ValueError(f"Invalid chain: {chain}")
        self.chain = chain
        self.subgraph_url = {}

        self.custom_price_logic: Dict[str, Callable] = {
            # do not checksum
            "0xf1617882a71467534d14eee865922de1395c9e89": self._saETH,
            "0xfc87753df5ef5c368b5fba8d4c5043b77e8c5b39": self._aETH,
        }

    def get_subgraph_url(self, subgraph="core") -> str:
        """
        perform some soup magic to determine the latest subgraph url

        sources used (in order of priority):
        1. sdk config file
        2. frontend v2 config file
        3. frontend v2 config file (legacy style; for chains not supported by decentralised the graph)

        params:
        - subgraph: "apiv3", "core", "gauges", "blocks" or "aura"

        returns:
        - https url of the subgraph
        """
        if subgraph == "apiv3":
            return "https://api-v3.balancer.fi"

        if subgraph == "aura":
            return AURA_SUBGRAPHS_BY_CHAIN.get(self.chain, None)

        return (
            self.get_subgraph_url_frontendv2(subgraph)
            or self.get_subgraph_url_legacy(subgraph)
            or self.get_subgraph_url_sdk(subgraph)
            or None
        )

    def get_subgraph_url_frontendv2(self, subgraph):
        if subgraph == "core":
            magic_word = "main:"
        elif subgraph == "gauges":
            magic_word = "gauge:"
        elif subgraph == "blocks":
            magic_word = "blocks:"

        # get subgraph url from frontend config
        chain_url_slug = "gnosis-chain" if self.chain == "gnosis" else self.chain
        config_file = f"https://raw.githubusercontent.com/balancer/frontend-v2/master/src/lib/config/{chain_url_slug}/index.ts"
        found_magic_word = False
        with urlopen(config_file) as f:
            for line in f:
                if found_magic_word or magic_word + " `" in str(line):
                    # url is on this line
                    r = re.search("`(.*)`", line.decode("utf-8"))
                    try:
                        url = r.group(1)
                        if urlparse(url).scheme in ["http", "https"]:
                            graph_api_key = os.getenv("GRAPH_API_KEY")
                            if "${keys.graph}" in url and not graph_api_key:
                                break
                            return url.replace("${keys.graph}", graph_api_key)
                    except AttributeError:
                        break
                if magic_word in str(line):
                    # url is on next line, return it on the next iteration
                    found_magic_word = True
        return None

    def get_subgraph_url_sdk(self, subgraph):
        if subgraph == "core":
            magic_word = "subgraph:"
        elif subgraph == "gauges":
            magic_word = "gaugesSubgraph:"
        elif subgraph == "blocks":
            magic_word = "blockNumberSubgraph:"

        # get subgraph url from sdk config
        sdk_file = f"https://raw.githubusercontent.com/balancer/balancer-sdk/develop/balancer-js/src/lib/constants/config.ts"
        found_magic_word = False
        urls_reached = False
        with urlopen(sdk_file) as f:
            for line in f:
                if "[Network." in str(line):
                    chain_detected = (
                        str(line).split("[Network.")[1].split("]")[0].lower()
                    )
                    if chain_detected == self.chain:
                        for line in f:
                            if "urls: {" in str(line) or urls_reached:
                                urls_reached = True
                                if "}," in str(line):
                                    return None
                                if found_magic_word:
                                    url = (
                                        line.decode("utf-8")
                                        .strip()
                                        .split(",")[0]
                                        .strip(" ,'")
                                    )
                                    url = re.sub(
                                        r"(\s|\u180B|\u200B|\u200C|\u200D|\u2060|\uFEFF)+",
                                        "",
                                        url,
                                    )
                                    if urlparse(url).scheme in ["http", "https"]:
                                        return url
                                if magic_word in str(line):
                                    # url is on next line, return it on the next iteration
                                    found_magic_word = True
        return None

    def get_subgraph_url_legacy(self, subgraph):
        if subgraph == "core":
            magic_word = "main: ["
        elif subgraph == "gauges":
            magic_word = "gauge:"
        elif subgraph == "blocks":
            magic_word = "blocks:"

        chain_url_slug = "gnosis-chain" if self.chain == "gnosis" else self.chain
        config_file = f"https://raw.githubusercontent.com/balancer/frontend-v2/develop/src/lib/config/{chain_url_slug}/index.ts"

        found_magic_word = False
        with urlopen(config_file) as f:
            for line in f:
                if found_magic_word:
                    url = line.decode("utf-8").strip().strip(" ,'")
                    if urlparse(url).scheme in ["http", "https"]:
                        return url
                if magic_word + " " in str(line):
                    # url is on same line
                    url = line.decode("utf-8").split(magic_word)[1].strip().strip(",'")
                    if urlparse(url).scheme in ["http", "https"]:
                        return url
                if magic_word in str(line):
                    # url is on next line, return it on the next iteration
                    found_magic_word = True
        return None

    def fetch_graphql_data(
        self,
        subgraph: str,
        query: str,
        params: dict = None,
        url: str = None,
        retries: int = 2,
    ):
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
            if not self.subgraph_url.get(subgraph):
                self.subgraph_url[subgraph] = self.get_subgraph_url(subgraph)
                if not self.subgraph_url.get(subgraph):
                    raise ValueError(
                        f"Subgraph url not found for {subgraph} on chain {self.chain}"
                    )

        transport = RequestsHTTPTransport(
            url=url or self.subgraph_url[subgraph], retries=retries
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        # retrieve the query from its file and execute it
        with open(f"{graphql_base_path}/{subgraph}/{query}.gql") as f:
            gql_query = gql(f.read())
        result = client.execute(gql_query, variable_values=params)

        return result

    def get_first_block_after_utc_timestamp(self, timestamp: int) -> int:
        if timestamp > int(datetime.now().strftime("%s")):
            timestamp = int(datetime.now().strftime("%s")) - 2000

        data = self.fetch_graphql_data(
            "blocks",
            "first_block_after_ts",
            {
                "timestamp_gt": int(timestamp) - 200,
                "timestamp_lt": int(timestamp) + 200,
            },
        )
        data["blocks"].sort(key=lambda x: x["timestamp"], reverse=True)
        return int(data["blocks"][0]["number"])

    def get_twap_price_token(
        self,
        addresses: Union[List[str], str],
        chain: GqlChain,
        date_range: DateRange,
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
        current_ts = int(datetime.now(timezone.utc).timestamp())
        one_year_ago_ts = int(
            (datetime.now(timezone.utc) - timedelta(days=365)).timestamp()
        )

        margin = 24 * 3600

        if not (
            one_year_ago_ts - margin <= start_date_ts <= current_ts + margin
            and one_year_ago_ts - margin <= end_date_ts <= current_ts + margin
        ):
            raise ValueError("date range should be within the past year")

        chain = chain.value if isinstance(chain, GqlChain) else chain.upper()
        params = {"addresses": addresses, "chain": chain, "range": "ONE_YEAR"}

        token_data = self.fetch_graphql_data(
            "apiv3",
            "get_historical_token_prices",
            params,
        )

        def calc_twap(address: str) -> TWAPResult:
            prices = [
                Decimal(item["price"])
                for entry in token_data["tokenGetHistoricalPrices"]
                if entry["address"] == address
                and entry["chain"].lower() == chain.lower()
                for item in entry["prices"]
                if end_date_ts >= int(item["timestamp"]) >= start_date_ts
            ]
            if not prices:
                return None
            return TWAPResult(address=address, twap_price=sum(prices) / len(prices))

        results = [calc_twap(addr) for addr in addresses]
        return results[0] if len(results) == 1 else results

    def get_twap_price_pool(
        self,
        pool_id: str,
        chain: GqlChain,
        date_range: DateRange,
        web3: Web3 = None,
        block: int = None,
    ) -> TwapPrices:
        """
        fetches the TWAP price of a pool's BPT and its tokens over the given `date_range`.
        if web3 and a block are passed, the function will calculate the total supply of the pool at the given block

        params:
        - pool_id: the id of the pool
        - chain: the chain network from GqlChain enum
        - date_range: tuple of (start_date_ts, end_date_ts)

        returns:
        - TwapPrices(bpt_price: Decimal, token_prices: List[TWAPResult])
        """

        chain = chain.value if isinstance(chain, GqlChain) else chain.upper()
        params = {
            "chain": chain,
            "id": pool_id,
        }

        token_data = self.fetch_graphql_data(
            "apiv3",
            "get_pool_tokens",
            params,
        )["poolGetPool"]

        # NOTE: dont checksum token addresses, api doesnt recognize them
        token_addresses = [token["address"] for token in token_data["poolTokens"]]
        bpt_address = pool_id[:42]

        if web3 and block:
            balancer_pool_address = Web3.to_checksum_address(pool_id[:42])
            weighed_pool_contract = web3.eth.contract(
                address=balancer_pool_address,
                abi=get_abi("WeighedPool"),
            )
            decimals = weighed_pool_contract.functions.decimals().call()
            bpt_supply = Decimal(
                weighed_pool_contract.functions.totalSupply().call(
                    block_identifier=block
                )
                / 10**decimals
            )
        else:
            # sometimes the bpt address is part of the `poolTokens`
            if bpt_address in token_addresses:
                bpt_loc = token_addresses.index(bpt_address)
                bpt_supply = Decimal(token_data["poolTokens"][bpt_loc]["balance"])
                token_addresses.remove(bpt_address)
            else:
                bpt_supply = Decimal(token_data["dynamicData"]["totalShares"])

        twap_results: List[TWAPResult] = []

        custom_price_tokens = [
            address
            for address in token_addresses
            if self.custom_price_logic.get(address)
        ]
        standard_price_tokens = [
            address
            for address in token_addresses
            if address not in custom_price_tokens and address != bpt_address
        ]

        for address in custom_price_tokens:
            custom_price_logic = self.custom_price_logic.get(address)
            twap_results.append(
                custom_price_logic(
                    address=address,
                    chain=chain,
                    date_range=date_range,
                    web3=web3,
                    block=block,
                )
            )

        if standard_price_tokens:
            res = self.get_twap_price_token(
                addresses=standard_price_tokens,
                chain=chain,
                date_range=date_range,
            )
            (
                twap_results.extend(res)
                if isinstance(res, list)
                else twap_results.append(res)
            )

        bpt_price = (
            sum(
                Decimal(token["balance"]) * twap_result.twap_price
                for token, twap_result in zip(token_data["poolTokens"], twap_results)
            )
            / bpt_supply
        )

        return TwapPrices(bpt_price=bpt_price, token_prices=twap_results)

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
        res = self.fetch_graphql_data("apiv3", "vebal_get_voting_list")
        return [Pool(**pool) for pool in res["veBalGetVotingList"]]

    def get_balancer_pool_snapshots(
        self,
        block: int = None,
        timestamp: int = None,
        pools_per_req: int = 1000,
        limit: int = 5000,
    ) -> List[PoolSnapshot]:
        if not any([block, timestamp]):
            raise ValueError("Must pass either block or timestamp")

        block = block or self.get_first_block_after_utc_timestamp(timestamp)

        all_pools = []
        offset = 0
        while True:
            result = self.fetch_graphql_data(
                "core",
                "pool_snapshots",
                {"first": pools_per_req, "skip": offset, "block": block},
            )
            all_pools.extend(
                [
                    PoolSnapshot(**flatten_nested_dict(pool))
                    for pool in result["poolSnapshots"]
                ]
            )
            offset += pools_per_req
            if offset >= limit:
                break
            if len(result["poolSnapshots"]) < pools_per_req:
                break
        return all_pools

    def _saETH(
        self,
        address: str,
        chain: str,
        date_range: DateRange,
        web3: Web3 = None,
        block: int = None,
    ) -> TWAPResult:
        if not web3 and not block:
            raise ValueError("need `web3` and `block` to calculate saETH TWAP")

        saeth = web3.eth.contract(
            address=web3.to_checksum_address(address),
            abi=get_abi("saETH"),
        )

        shares = Decimal(
            saeth.functions.convertToShares(int(1e18)).call(block_identifier=block)
            / int(1e18)
        )

        res = self.get_twap_price_token(
            addresses=["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"],
            chain=chain,
            date_range=date_range,
        )
        return TWAPResult(address=address, twap_price=res.twap_price * shares)

    def _aETH(
        self,
        address: str,
        chain: str,
        date_range: DateRange,
        web3: Web3 = None,
        block: int = None,
    ) -> TWAPResult:
        # pegged to eth
        prices = self.get_twap_price_token(
            addresses=["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"],
            chain=chain,
            date_range=date_range,
        )
        return TWAPResult(address=address, twap_price=prices.twap_price)
