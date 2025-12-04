from decimal import Decimal
from bal_tools.ecosystem import HiddenHand


def test_get_min_aura_incentive():
    hh = HiddenHand()
    result = hh.get_min_aura_incentive()

    assert isinstance(result, Decimal)
