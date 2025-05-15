import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
from pydantic import validate_arguments
from models.config import LotteryConfig

class DataHandler:
    def __init__(self, config: LotteryConfig):
        self.config = config
        self.historical: Optional[pd.DataFrame] = None
        self.upcoming: Optional[pd.DataFrame] = None
        self.latest_draw: Optional[pd.Series] = None

    def prepare_filesystem(self) -> None:
        """Create required directories"""
        Path(self.config.data.stats_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.data.results_dir).mkdir(parents=True, exist_ok=True)

    @validate_arguments
    def load_data(self) -> None:
        """Load and validate all data files"""
        self._load_historical()
        self._load_upcoming()
        self._load_latest()

    def _load_historical(self) -> None:
        """Load historical draws data"""
        num_cols = self._get_number_columns()
        self.historical = pd.read_csv(
            self.config.data.historical_path,
            header=None,
            names=['date', 'numbers'],
            dtype={'date': str, 'numbers': str}
        )
        self.historical[num_cols] = self.historical['numbers'].str.split('-', expand=True).astype(int)
        self.historical['date'] = pd.to_datetime(self.historical['date'], format='%m/%d/%y')
        self._validate_data(self.historical)

    def _load_upcoming(self) -> None:
        """Load upcoming draws if configured"""
        if not self.config.data.upcoming_path.strip():
            return
            
        num_cols = self._get_number_columns()
        try:
            self.upcoming = pd.read_csv(
                self.config.data.upcoming_path,
                header=None,
                names=['date', 'numbers']
            )
            self.upcoming[num_cols] = self.upcoming['numbers'].str.split('-', expand=True).astype(int)
            self.upcoming['date'] = pd.to_datetime(self.upcoming['date'], format='%m/%d/%y')
            self._validate_data(self.upcoming)
            
            if self.config.data.merge_upcoming:
                self.historical = pd.concat([self.historical, self.upcoming])
        except FileNotFoundError:
            if self.config.output.verbose:
                print("Note: Upcoming draws file not found")

    def _load_latest(self) -> None:
        """Load latest draw if available"""
        if not self.config.data.latest_path.strip():
            return
            
        num_cols = self._get_number_columns()
        try:
            latest = pd.read_csv(
                self.config.data.latest_path,
                header=None,
                names=['date', 'numbers']
            )
            if not latest.empty:
                latest[num_cols] = latest['numbers'].str.split('-', expand=True).astype(int)
                latest['date'] = pd.to_datetime(latest['date'], format='%m/%d/%y')
                self._validate_data(latest)
                self.latest_draw = latest.iloc[-1]
        except (FileNotFoundError, pd.errors.EmptyDataError):
            if self.config.output.verbose:
                print("Note: Latest draw file not found or empty")

    def _get_number_columns(self) -> list:
        """Generate column names for numbers"""
        return [f'n{i+1}' for i in range(self.config.strategy.numbers_to_select)]

    def _validate_data(self, df: pd.DataFrame) -> None:
        """Validate data integrity"""
        num_cols = self._get_number_columns()
        max_num = self.config.strategy.number_pool
        
        for col in num_cols:
            invalid = df[
                (df[col] < 1) | 
                (df[col] > max_num)
            ]
            if not invalid.empty:
                raise ValueError(
                    f"Invalid numbers found in column {col} (range 1-{max_num})"
                )