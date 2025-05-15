import pytest
from core.analyzer import LotteryAnalyzer
from models.config import LotteryConfig
import pandas as pd

@pytest.fixture
def sample_config():
    return LotteryConfig(
        data={...},
        strategy={
            'number_pool': 10,
            'numbers_to_select': 3,
            ...
        },
        ...
    )

@pytest.fixture 
def sample_data():
    return pd.DataFrame({
        'date': ['01/01/23', '01/02/23'],
        'numbers': ['1-2-3', '4-5-6'],
        'n1': [1, 4],
        'n2': [2, 5],
        'n3': [3, 6]
    })

def test_frequency_analysis(sample_config, sample_data):
    analyzer = LotteryAnalyzer(sample_data, sample_config)
    freq = analyzer.analyze_frequency()
    assert freq[1] == 1
    assert freq[4] == 1