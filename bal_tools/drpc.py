from web3 import Web3
from bal_addresses import AddrBook

DRPC_NAME_OVERRIDES = {
    "mainnet": "ethereum",
    "zkevm": "polygon-zkevm",
}

class Web3RpcByChain:
    def __init__(self, DRPC_KEY):
        self.DRPC_KEY = DRPC_KEY
        self.w3_by_chain = {}
        for chain in AddrBook.chain_ids_by_name.keys():
            try:
                w3 = Web3Rpc(chain, DRPC_KEY)
                self.w3_by_chain[chain] = w3
            except ConnectionError as e:
                print(f"Skipping chain {chain} due to connection error: {e}")

    def __getitem__(self, chain):
        return self.w3_by_chain[chain]

    def __setitem__(self, chain, value):
        self.w3_by_chain[chain] = value

    def __delitem__(self, chain):
        del self.w3_by_chain[chain]

    def __iter__(self):
        return iter(self.w3_by_chain)

    def keys(self):
        return self.w3_by_chain.keys()

    def values(self):
        return self.w3_by_chain.values()

    def items(self):
        return self.w3_by_chain.items()

class Web3Rpc:
    def __init__(self, chain, DRPC_KEY):
        drpc_chain = DRPC_NAME_OVERRIDES.get(chain, chain)
        self.w3 = Web3(Web3.HTTPProvider(f"https://lb.drpc.org/ogrpc?network={drpc_chain}&dkey={DRPC_KEY}"))
        if not self.w3.is_connected():
            raise ConnectionError(f"Unable to connect to {drpc_chain} network with provided DRPC_KEY.")
        try:
            self.w3.eth.block_number
        except Exception as e:
            raise ConnectionError(f"Error fetching latest block number: {e}, chain: {chain}, url: {self.w3.provider.endpoint_uri}")

    def __getattr__(self, name):
        return getattr(self.w3, name)
