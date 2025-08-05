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


def test_tuple_type_preservation(reward_distributor_abi):
    """Test that tuple types with components are preserved in the output, not collapsed."""
    builder = SafeTxBuilder("0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f")
    reward_distributor_address = "0x0000000000000000000000000000000000000001"

    reward_distributor = SafeContract(
        reward_distributor_address, reward_distributor_abi
    )

    claims = [
        [
            "0x1234567890123456789012345678901234567890123456789012345678901234",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            1000000000000000000,
            [
                "0xabcdef1234567890123456789012345678901234567890123456789012345678",
                "0xfedcba0987654321098765432109876543210987654321098765432109876543",
            ],
        ]
    ]
    reward_distributor.claim(claims)

    payload = builder.base_payload

    assert len(payload.transactions) == 1
    tx = payload.transactions[0]

    assert tx.to == reward_distributor_address
    assert tx.contractMethod.name == "claim"

    # Verify the input has the correct type (tuple[])
    assert len(tx.contractMethod.inputs) == 1
    claim_input = tx.contractMethod.inputs[0]

    # Check that the type is preserved as "tuple[]"
    assert claim_input.name == "_claims"
    assert claim_input.type == "tuple[]"
    assert claim_input.internalType == "struct RewardDistributor.Claim[]"

    assert hasattr(claim_input, "components"), "Input should have components attribute"
    assert claim_input.components is not None, "Components should not be None"
    assert (
        len(claim_input.components) == 4
    ), "Should have 4 components in the Claim struct"

    # Verify the input values are correctly stored
    assert "_claims" in tx.contractInputsValues
    assert tx.contractInputsValues["_claims"] == str(claims)
