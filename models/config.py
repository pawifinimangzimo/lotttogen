from pydantic import BaseModel, confloat, conint
from typing import Dict, List, Optional

class DataConfig(BaseModel):
    latest_path: str
    historical_path: str
    upcoming_path: str
    stats_dir: str
    results_dir: str
    merge_upcoming: bool
    archive_upcoming: bool

class ValidationConfig(BaseModel):
    mode: str
    test_draws: conint(gt=0)
    alert_threshold: conint(ge=1, le=6)
    save_report: bool

class StrategyConfig(BaseModel):
    number_pool: conint(gt=1)
    numbers_to_select: conint(gt=1)
    frequency_weight: confloat(ge=0, le=1)
    recent_weight: confloat(ge=0, le=1)
    random_weight: confloat(ge=0, le=1)
    low_number_max: conint(gt=0)
    low_number_chance: confloat(ge=0, le=1)
    high_prime_min: conint(gt=0)
    high_prime_chance: confloat(ge=0, le=1)
    cold_threshold: conint(gt=0)
    resurgence_threshold: conint(ge=0)

class RecencyBinsConfig(BaseModel):
    hot: conint(gt=0)
    warm: conint(gt=0)
    cold: conint(gt=0)

class CombinationAnalysisConfig(BaseModel):
    pairs: bool
    triplets: bool
    quadruplets: bool
    quintuplets: bool
    sixtuplets: bool

class AnalysisConfig(BaseModel):
    default_match_threshold: conint(ge=1, le=6)
    default_show_top: conint(gt=0)
    min_display_matches: conint(ge=0)
    recency_units: str
    recency_bins: RecencyBinsConfig
    show_combined_stats: bool
    top_range: conint(gt=0)
    combination_analysis: CombinationAnalysisConfig
    min_combination_count: conint(ge=1)

class OutputConfig(BaseModel):
    sets_to_generate: conint(gt=0)
    save_analysis: bool
    verbose: bool

class LotteryConfig(BaseModel):
    data: DataConfig
    validation: ValidationConfig
    strategy: StrategyConfig
    output: OutputConfig
    analysis: AnalysisConfig