import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[2])
sys.path.append(project_root)

from bal_tools.subgraph import Subgraph, GqlChain
from bal_tools.pools_gauges import BalPoolsGauges


# generate price data from mainnet core pools to test against for Subgraph.get_twap_price_pool
# NOTE: assumes that the current implementation of get_twap_price_pool is correct
# results should be verified against other sources before using this to test against
def gen_price_data_for_date_range(date_range: tuple[int, int]):
    subgraph = Subgraph()
    mainnet_core_pools = BalPoolsGauges().core_pools

    pool_prices = {}
    for pool_id, symbol in mainnet_core_pools:
        prices = subgraph.get_twap_price_pool(
            pool_id=pool_id,
            chain=GqlChain.MAINNET,
            date_range=date_range,
        )
        # cant json serialize Decimal objects
        pool_prices[symbol] = {
            "bpt_price": float(prices.bpt_price.twap_price),
            "token_prices": [
                {"address": price.address, "twap_price": float(price.twap_price)}
                for price in prices.token_prices
            ]
        }

    price_data_output = f"tests/price_data/pool_prices-{date_range[0]}-{date_range[1]}.json"
    with open(price_data_output, "w") as f:
        json.dump(pool_prices, f)

    print(f"Price data saved to {price_data_output}")

def parse_date(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate price data for a date range")
    parser.add_argument("--start_date", help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", help="End date in YYYY-MM-DD format")
    
    args = parser.parse_args()

    start_timestamp = parse_date(args.start_date)
    end_timestamp = parse_date(args.end_date)
    
    gen_price_data_for_date_range((start_timestamp, end_timestamp))
