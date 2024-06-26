from urllib.request import urlopen
import os
import re

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from bal_addresses import AddrBook


graphql_base_path = f"{os.path.dirname(os.path.abspath(__file__))}/graphql"

AURA_SUBGRAPHS_BY_CHAIN = {
    "mainnet": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-mainnet/api",
    "arbitrum": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-arbitrum/api",
    "optimism": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-optimism/api",
    "gnosis": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-gnosis/api",
    "base": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-base/api",
    "polygon": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-polygon/api",
    "zkevm": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-zkevm/api",
    "avalanche": "https://subgraph.satsuma-prod.com/cae76ab408ca/1xhub-ltd/aura-finance-avalanche/api",
}


class Subgraph:
    def __init__(self, chain: str):
        if chain not in AddrBook.chain_ids_by_name.keys():
            raise ValueError(f"Invalid chain: {chain}")
        self.chain = chain
        self.subgraph_url = {}

    def get_subgraph_url(self, subgraph="core") -> str:
        """
        perform some soup magic to determine the latest subgraph url used in the official frontend

        params:
        - subgraph: "core", "gauges" , "blocks" or "aura"

        returns:
        - https url of the subgraph
        """
        if subgraph == "core":
            magic_word = "subgraph:\n"
        elif subgraph == "gauges":
            magic_word = "gaugesSubgraph:\n"
        elif subgraph == "blocks":
            magic_word = "blockNumberSubgraph:\n"
        elif subgraph == "aura":
            return AURA_SUBGRAPHS_BY_CHAIN.get(self.chain, None)

        # get subgraph url from sdk config
        sdk_file = f"https://raw.githubusercontent.com/balancer/balancer-sdk/develop/balancer-js/src/lib/constants/config.ts"
        found_magic_word = False
        with urlopen(sdk_file) as f:
            for line in f:
                if '[Network.' in str(line):
                    chain_detected = str(line).split('[Network.')[1].split(']')[0].lower()
                    if chain_detected == self.chain:
                        for line in f:
                            if found_magic_word:
                                url = line.decode("utf-8").strip().split(',')[0].strip(" ,'")
                                url = re.sub(r'(\s|\u180B|\u200B|\u200C|\u200D|\u2060|\uFEFF)+', '', url)
                                return url
                            if magic_word in str(line):
                                # url is on next line, return it on the next iteration
                                found_magic_word = True

    def fetch_graphql_data(self, subgraph: str, query: str, params: dict = None):
        """
        query a subgraph using a locally saved query

        params:
        - query: the name of the query (file) to be executed
        - params: optional parameters to be passed to the query

        returns:
        - result of the query
        """
        # build the client
        if self.subgraph_url.get(subgraph) is None:
            self.subgraph_url[subgraph] = self.get_subgraph_url(subgraph)
        transport = RequestsHTTPTransport(
            url=self.subgraph_url[subgraph],
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
