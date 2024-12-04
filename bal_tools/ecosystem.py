from collections import defaultdict
import re
from typing import Dict, List
from .errors import (
    UnexpectedListLengthError,
    MultipleMatchesError,
    NoResultError,
)
from web3 import Web3
import requests
from .subgraph import Subgraph
from .utils import to_checksum_address
from .models import PropData


AURA_L2_DEFAULT_GAUGE_STAKER = to_checksum_address(
    "0xC181Edc719480bd089b94647c2Dc504e2700a2B0"
)


class KeyAsDefaultDict(defaultdict):
    def __missing__(self, key):
        return key


class Aura:
    ## Aura seems to stake from the same address on all chains except mainnet
    AURA_GAUGE_STAKER_BY_CHAIN = defaultdict(lambda: AURA_L2_DEFAULT_GAUGE_STAKER)
    AURA_GAUGE_STAKER_BY_CHAIN["mainnet"] = to_checksum_address(
        "0xaF52695E1bB01A16D33D7194C28C42b10e0Dbec2"
    )

    def __init__(self, chain):
        self.chain = chain
        self.subgraph = Subgraph(chain)
        try:
            self.aura_pids_by_address = Aura.get_aura_gauge_mappings(self)
        except Exception as e:
            print(f"Failed to populate aura pids from aura subgraph: {e}")
            self.aura_pids_by_address = None

    def get_aura_gauge_mappings(self) -> Dict[str, int]:
        """
        Get a dict with gauge_address as key and aura PID as value for the running chain.
        """
        data = self.subgraph.fetch_graphql_data("aura", "get_aura_gauge_mappings")
        # print(json.dumps(data, indent=1))
        aura_pid_by_gauge = {}
        for result_item in data["gauges"]:
            gauge_address = to_checksum_address(result_item["pool"]["gauge"]["id"])
            pid = result_item["pool"]["id"]
            # Seems like pid can be a string or a list
            if isinstance(pid, list):
                if len(pid > 1):
                    raise MultipleMatchesError(
                        f"Gauge: {gauge_address} is returning multiple aura PIDs: {pid}"
                    )
                else:
                    pid = [pid][0]

            if gauge_address in aura_pid_by_gauge:
                raise MultipleMatchesError(
                    f"Gauge with address{gauge_address} already found with PID"
                    f" {aura_pid_by_gauge[gauge_address]} when trying to"
                    f" insert new PID {pid}"
                )
            aura_pid_by_gauge[gauge_address] = pid
        return aura_pid_by_gauge

    def get_aura_pool_shares(self, gauge_address, block) -> Dict[str, int]:
        """
        Get a dict with user address as key and wei balance staked in aura as value for the specified gauge and block

        params:
        - gauge: The gauge to query that has BPTs deposited in it
        - block: The block to query on

        returns:
        - result of the query
        """
        # Prepare the GraphQL query and variables
        gauge_address = to_checksum_address(gauge_address)
        aura_pid = self.aura_pids_by_address.get(gauge_address)
        variables = {"poolId": aura_pid, "block": int(block)}
        try:
            data = self.subgraph.fetch_graphql_data(
                "aura", "get_aura_user_pool_balances", variables
            )
        except Exception as e:
            raise NoResultError(f"Problem executing subgraph query: {e}")

        results = {}
        # Parse the data if the query was successful
        if data and "leaderboard" in data and data["leaderboard"]["accounts"]:
            for account in data["leaderboard"]["accounts"]:
                ## Aura amounts are WEI denominated and others are float.  Transform
                amount = float(int(account["staked"]) / 1e18)
                user_address = to_checksum_address(account["account"]["id"])
                results[user_address] = amount
        # TODO better handle pagination with the query and this function/pull multiple pages if required
        assert len(results) < 1000, "Pagination limit hit on Aura query"
        return results

    def get_aura_pid_from_gauge(self, deposit_gauge_address: str) -> int:
        """
        Get the Aura PID for a given Balancer Gauge

        params:
        - deposit_gauge_address: The gauge to query that has BPTs deposited in it

        returns:
        - The Aura PID of the specified gauge
        """
        deposit_gauge_address = to_checksum_address(deposit_gauge_address)
        try:
            result = self.aura_pids_by_address.get(deposit_gauge_address, None)
        except Exception as e:
            raise NoResultError(f"Problem executing subgraph query: {e}")
        if not result:
            raise NoResultError(f"Gauge {deposit_gauge_address} has no Aura PID")
        if isinstance(result, str):
            return result
        else:
            if len(result) != 1:
                raise UnexpectedListLengthError(
                    "Got a list result with something other than 1 member"
                    f" when compiling aura PID mapping: {result}"
                )
            return result[0]


class Snapshot:
    SNAPSHOT_STATE_CLOSED = "closed"
    SNAPSHOT_MIN_AMOUNT_POOLS = 10

    def __init__(self):
        self.subgraph = Subgraph()

    def get_previous_snapshot_round(
        self, web3: Web3, space: str = "gauges.aurafinance.eth"
    ):
        limit = 100
        offset = 0
        while True:
            result = self.subgraph.fetch_graphql_data(
                subgraph="snapshot",
                query="GetActiveProposals",
                params={"first": limit, "skip": offset, "space": space},
            )
            offset += limit
            if not result or not result.get("proposals"):
                break
            gauge_proposal = None
            for proposal in result["proposals"]:
                if proposal["state"] != self.SNAPSHOT_STATE_CLOSED:
                    continue
                match = re.match(r"Gauge Weight for Week of .+", proposal["title"])
                number_of_choices = len(proposal["choices"])
                current_timestamp = web3.eth.get_block(web3.eth.get_block_number())[
                    "timestamp"
                ]
                timestamp_two_weeks_ago = current_timestamp - (60 * 60 * 24 * 7 * 2)
                if match and number_of_choices > self.SNAPSHOT_MIN_AMOUNT_POOLS:
                    if timestamp_two_weeks_ago < proposal["end"] < current_timestamp:
                        gauge_proposal = proposal
                        break
            return gauge_proposal

    def get_votes_from_snapshot(self, snapshot_id: str):
        limit = 100
        offset = 0
        while True:
            result = self.subgraph.fetch_graphql_data(
                subgraph="snapshot",
                query="GetProposalVotes",
                params={
                    "first": limit,
                    "skip": offset,
                    "snapshot_id": snapshot_id,
                    "voter": "multisigs/maxi_omni",
                    "space": "gauges.aurafinance.eth",
                },
            )
            offset += limit
            if not result or not result.get("votes"):
                break
            votes = result["votes"][0]
            if not votes:
                continue
            votes = votes["choice"]
            return votes


class HiddenHand:
    AURA_URL = "https://api.hiddenhand.finance/proposal/aura"

    def fetch_aura_bribs(self) -> List[PropData]:
        """
        Fetch GET bribes from hidden hand api
        """
        res = requests.get(self.AURA_URL)
        if not res.ok:
            raise ValueError("Error fetching bribes from hidden hand api")

        res_parsed = res.json()
        if res_parsed["error"]:
            raise ValueError("HH API returned error")
        return [PropData(**prop_data) for prop_data in res_parsed["data"]]
