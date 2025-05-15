from collections import defaultdict
from typing import Dict, List, Set, Tuple
import numpy as np
import pandas as pd
import sympy
from itertools import combinations
from tabulate import tabulate
from models.config import LotteryConfig

class LotteryAnalyzer:
    def __init__(self, historical_data: pd.DataFrame, config: LotteryConfig):
        self.historical = historical_data
        self.config = config
        self.number_cols = self._get_number_columns()
        self.number_pool = list(range(1, self.config.strategy.number_pool + 1))
        self.prime_numbers = self._get_prime_numbers()
        
    def analyze_all(self) -> Dict:
        """Run all analyses and return consolidated results"""
        return {
            'frequency': self.analyze_frequency(),
            'recency': self.analyze_recency(),
            'temperature': self.classify_temperature(),
            'combinations': self.analyze_combinations(),
            'cold_numbers': self.identify_cold_numbers(),
            'prime_numbers': self.prime_numbers
        }

    def analyze_frequency(self) -> pd.Series:
        """Calculate frequency of each number"""
        numbers = self.historical[self.number_cols].values.flatten()
        return pd.Series(numbers).value_counts().sort_index()

    def analyze_recency(self) -> Dict[int, int]:
        """Calculate how many draws since each number last appeared"""
        recency = {}
        total_draws = len(self.historical)
        
        for num in self.number_pool:
            mask = self.historical[self.number_cols].eq(num).any(axis=1)
            last_occurrence = self.historical[mask].index.max()
            recency[num] = total_draws - self.historical.index.get_loc(last_occurrence) - 1
            
        return recency

    def classify_temperature(self) -> Dict[str, List[int]]:
        """Classify numbers as hot/warm/cold based on recency"""
        recency = self.analyze_recency()
        bins = self.config.analysis.recency_bins
        
        return {
            'hot': [n for n, r in recency.items() if r <= bins.hot],
            'warm': [n for n, r in recency.items() if bins.hot < r <= bins.warm],
            'cold': [n for n, r in recency.items() if r > bins.cold]
        }

    def identify_cold_numbers(self) -> Set[int]:
        """Identify numbers not drawn recently"""
        last_n_draws = self.historical.iloc[-self.config.strategy.cold_threshold:][self.number_cols].values.flatten()
        return set(self.number_pool) - set(last_n_draws)

    def analyze_combinations(self) -> Dict:
        """Analyze number pairs, triplets, etc."""
        combo_stats = defaultdict(lambda: defaultdict(int))
        
        for _, row in self.historical.iterrows():
            nums = sorted(row[self.number_cols])
            for size in range(2, len(nums) + 1):
                if not self._should_analyze_combination_size(size):
                    continue
                    
                for combo in combinations(nums, size):
                    combo_key = f'size_{size}'
                    combo_stats[combo_key][combo] += 1
                    for num in combo:
                        combo_stats[f'num_in_{combo_key}'][num] += 1
        
        return self._format_combination_results(combo_stats)

    def _should_analyze_combination_size(self, size: int) -> bool:
        """Check if combination size should be analyzed based on config"""
        combo_config = self.config.analysis.combination_analysis
        return (
            (size == 2 and combo_config.pairs) or
            (size == 3 and combo_config.triplets) or
            (size == 4 and combo_config.quadruplets) or
            (size == 5 and combo_config.quintuplets) or
            (size == 6 and combo_config.sixtuplets)
        )

    def _format_combination_results(self, combo_stats: Dict) -> Dict:
        """Format combination results for display"""
        results = {}
        top_n = self.config.analysis.top_range
        
        # Process combinations
        for size in range(2, 7):
            combo_key = f'size_{size}'
            if combo_key in combo_stats:
                filtered = {k:v for k,v in combo_stats[combo_key].items() 
                           if v >= self.config.analysis.min_combination_count}
                display_name = self._get_combo_display_name(size)
                results[combo_key] = tabulate(
                    sorted(filtered.items(), key=lambda x: -x[1])[:top_n],
                    headers=[display_name, 'Count'],
                    tablefmt='grid'
                )
        
        # Process number participation
        for size in range(2, 7):
            part_key = f'num_in_size_{size}'
            if part_key in combo_stats:
                total_possible = len(self.historical) * (self.config.strategy.numbers_to_select - 1)
                display_name = f'Numbers in {self._get_combo_display_name(size)}'
                results[part_key] = tabulate(
                    sorted([(num, cnt, f"{cnt/total_possible:.1%}") 
                          for num, cnt in combo_stats[part_key].items()],
                         key=lambda x: -x[1])[:top_n],
                    headers=['Number', 'Count', 'Frequency'],
                    tablefmt='grid'
                )
        
        return results

    def _get_combo_display_name(self, size: int) -> str:
        """Get display name for combination size"""
        return {
            2: 'Pairs',
            3: 'Triplets',
            4: 'Quadruplets',
            5: 'Quintuplets',
            6: 'Sixtuplets'
        }[size]

    def _get_number_columns(self) -> List[str]:
        """Generate column names for numbers"""
        return [f'n{i+1}' for i in range(self.config.strategy.numbers_to_select)]

    def _get_prime_numbers(self) -> List[int]:
        """Identify prime numbers in the number pool"""
        return [n for n in self.number_pool if sympy.isprime(n)]