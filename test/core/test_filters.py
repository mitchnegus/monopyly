import pytest

from monopyly.core.filters import *


@pytest.mark.parametrize(
    'amount, currency_amount',
    [(10, '10.00'),
     (10.00, '10.00'),
     (29.99, '29.99'),
     (29.9999, '30.00'),
     (-0.00, '0.00'),
     (-39, '-39.00')]
)
def test_make_currency(amount, currency_amount):
    assert make_currency(amount) == currency_amount


@pytest.mark.parametrize(
    'integer, ordinal',
    [(1, '1st'),
     (2, '2nd'),
     (3, '3rd'),
     (4, '4th'),
     (5, '5th'),
     (10, '10th'),
     (11, '11th'),
     (21, '21st'),
     (100, '100th'),
     (101, '101st'),
     (102, '102nd'),
     (121, '121st'),
     (1000, '1000th')]
)
def test_make_ordinal(integer, ordinal):
    assert make_ordinal(integer) == ordinal
