from unittest.mock import patch

from monopyly.core.context_processors import *


@patch('monopyly.core.context_processors.date')
def test_inject_date_today(mock_date_module):
    mock_date_module.today.return_value = 12345 
    # Context processors must return a dictionary
    context_processor_dict = inject_date_today()
    assert context_processor_dict == {'date_today': '12345'}

