import logging
from models.config import LotteryConfig

def setup_logging(config: LotteryConfig):
    logging.basicConfig(
        level=logging.DEBUG if config.output.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )