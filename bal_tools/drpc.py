from web3 import Web3
from bal_addresses import AddrBook

DRPC_NAME_OVERRIDES = {
    "mainnet": "ethereum",
    "zkevm": "polygon-zkevm",
}

class W3_RPC_BY_CHAIN():
    w3_by_chain = {}

    def __init__(self, DRPC_KEY):
        self.DRPC_KEY = DRPC_KEY
        for chain in AddrBook.chain_ids_by_name.keys():
            drpc_chain = DRPC_NAME_OVERRIDES.get(chain, chain)
            self.w3_by_chain[chain] = W3_RPC(chain, DRPC_KEY)

class W3_RPC():
    def __init__(self, chain, DRPC_KEY):
        drpc_chain = self.DRPC_NAME_OVERRIDES.get(chain, chain)
        w3 = Web3(Web3.HTTPProvider(f"https://lb.drpc.org/ogrpc?network={drpc_chain}&dkey={DRPC_KEY}"))

