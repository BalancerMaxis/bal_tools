import pytest

from bal_tools.safe_tx_builder import SafeContract, SafeTxBuilder
from bal_tools.safe_tx_builder.models import BasePayload


def test_safe_contract(safe_tx_builder: SafeTxBuilder, erc20_abi, bribe_market_abi):
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    bribe_market_address = "0x45Bc37b18E73A42A4a826357a8348cDC042cCBBc"

    usdc = SafeContract(usdc_address, erc20_abi)
    usdc.approve(bribe_market_address, 100e18)

    bribe_market = SafeContract(bribe_market_address, bribe_market_abi)
    bribe_market.depositBribe(
        "0x0000000000000000000000000000000000000000000000000000000000000000",
        usdc_address,
        1e18,
        0,
        2,
    )

    payload = safe_tx_builder.output_payload("tests/payload_outputs/bribe.json")

    assert payload.transactions[0].to == usdc_address
    assert payload.transactions[0].contractMethod.name == "approve"
    assert payload.transactions[0].contractMethod.inputs[0].type == "address"
    assert payload.transactions[0].contractMethod.inputs[1].type == "uint256"
    assert (
        payload.transactions[0].contractInputsValues["_spender"] == bribe_market_address
    )
    assert payload.transactions[0].contractInputsValues["_value"] == str(int(100e18))

    assert payload.transactions[1].to == bribe_market_address
    assert payload.transactions[1].contractMethod.name == "depositBribe"
    assert payload.transactions[1].contractMethod.inputs[0].type == "bytes32"
    assert payload.transactions[1].contractMethod.inputs[1].type == "address"
    assert payload.transactions[1].contractMethod.inputs[2].type == "uint256"
    assert payload.transactions[1].contractMethod.inputs[3].type == "uint256"
    assert payload.transactions[1].contractMethod.inputs[4].type == "uint256"
    assert (
        payload.transactions[1].contractInputsValues["_proposal"]
        == "0x0000000000000000000000000000000000000000000000000000000000000000"
    )
    assert payload.transactions[1].contractInputsValues["_token"] == usdc_address
    assert payload.transactions[1].contractInputsValues["_amount"] == str(int(1e18))
    assert payload.transactions[1].contractInputsValues["_maxTokensPerVote"] == str(0)
    assert payload.transactions[1].contractInputsValues["_periods"] == str(2)


def test_multiple_functions_with_same_name(bridge_abi):
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    dao_msig = "0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f"
    builder = SafeTxBuilder(dao_msig)
    bridge = SafeContract("0x88ad09518695c6c3712AC10a214bE5109a655671", bridge_abi)

    bridge.relayTokens(usdc_address, dao_msig, int(1e18))
    bridge.relayTokens(usdc_address, int(1e18))

    builder.output_payload("tests/payload_outputs/multiple_names.json")
