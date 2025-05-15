import pytest
from models.config import LotteryConfig

@pytest.fixture
def default_config():
    return LotteryConfig(...)  # Full default config