from typing import List, Tuple
import numpy as np
from models.config import LotteryConfig
from core.analyzer import LotteryAnalyzer

class NumberSetGenerator:
    def __init__(self, analyzer: LotteryAnalyzer):
        self.analyzer = analyzer
        self.config = analyzer.config
        self.weights = self._calculate_initial_weights()

    def generate_sets(self) -> List[Tuple[List[int], str]]:
        """Generate number sets using different strategies"""
        strategies = [
            ('weighted_random', self._generate_weighted_random),
            ('high_low_mix', self._generate_high_low_mix),
            ('prime_balanced', self._generate_prime_balanced)
        ]
        
        sets_per_strategy = max(1, self.config.output.sets_to_generate // len(strategies))
        sets = []
        
        for name, strategy in strategies:
            for _ in range(sets_per_strategy):
                try:
                    numbers = strategy()
                    if self._is_valid_set(numbers):
                        sets.append((numbers, name))
                except Exception:
                    continue
        
        return sets

    def _calculate_initial_weights(self) -> np.ndarray:
        """Calculate initial weights for numbers"""
        freq = self.analyzer.analyze_frequency()
        recent = self._calculate_recent_counts()
        
        weights = np.ones(len(self.analyzer.number_pool))
        
        # Apply frequency weights
        if not freq.empty:
            freq_weights = (freq / freq.sum()).fillna(0)
            weights += freq_weights * self.config.strategy.frequency_weight * 10
        
        # Apply recency weights
        recent_weights = (recent / recent.sum()).fillna(0)
        weights += recent_weights * self.config.strategy.recent_weight * 5
        
        # Apply random component
        random_weights = np.random.dirichlet(np.ones(len(weights))) * 0.7
        weights += random_weights * self.config.strategy.random_weight * 15
        
        # Normalize
        return weights / weights.sum()

    def _calculate_recent_counts(self) -> pd.Series:
        """Count recent appearances of each number"""
        recent_draws = self.analyzer.historical.iloc[-int(len(self.analyzer.historical)*0.2):]
        recent_numbers = recent_draws[self.analyzer.number_cols].values.flatten()
        return pd.Series(recent_numbers).value_counts().reindex(
            self.analyzer.number_pool, fill_value=0
        )

    def _generate_weighted_random(self) -> List[int]:
        """Generate set using weighted random selection"""
        return sorted(np.random.choice(
            self.analyzer.number_pool,
            size=self.config.strategy.numbers_to_select,
            replace=False,
            p=self.weights
        ))

    def _generate_high_low_mix(self) -> List[int]:
        """Generate set with mix of high and low numbers"""
        low_max = self.config.strategy.low_number_max
        low_nums = [n for n in self.analyzer.number_pool if n <= low_max]
        high_nums = [n for n in self.analyzer.number_pool if n > low_max]
        
        split_point = self.config.strategy.numbers_to_select // 2
        selected = (
            list(np.random.choice(
                low_nums, 
                split_point, 
                replace=False,
                p=self.weights[low_nums]/self.weights[low_nums].sum()
            )) +
            list(np.random.choice(
                high_nums,
                self.config.strategy.numbers_to_select - split_point,
                replace=False,
                p=self.weights[high_nums]/self.weights[high_nums].sum()
            ))
        )
        return sorted(selected)

    def _generate_prime_balanced(self) -> List[int]:
        """Generate set with balanced prime numbers"""
        primes = self.analyzer.prime_numbers
        non_primes = [n for n in self.analyzer.number_pool if n not in primes]
        
        num_primes = np.random.choice([
            max(1, len(primes) // 3),
            len(primes) // 2,
            len(primes) // 2 + 1
        ])
        
        selected = (
            list(np.random.choice(
                primes,
                num_primes,
                replace=False,
                p=self.weights[primes]/self.weights[primes].sum()
            )) +
            list(np.random.choice(
                non_primes,
                self.config.strategy.numbers_to_select - num_primes,
                replace=False,
                p=self.weights[non_primes]/self.weights[non_primes].sum()
            ))
        )
        return sorted(selected)

    def _is_valid_set(self, numbers: List[int]) -> bool:
        """Validate generated number set"""
        return (
            len(numbers) == self.config.strategy.numbers_to_select and
            len(set(numbers)) == self.config.strategy.numbers_to_select and
            all(1 <= n <= self.config.strategy.number_pool for n in numbers)
        )