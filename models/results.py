from typing import Dict, List
from pydantic import BaseModel

class ValidationResult(BaseModel):
    draws_tested: int
    match_counts: Dict[int, int] = {i:0 for i in range(7)}
    best_per_draw: List[int] = []
    high_performance_sets: List[List[int]] = []
    match_percentages: Dict[str, str] = {}

    def calculate_percentages(self, num_sets: int) -> None:
        """Calculate match percentages"""
        total_comparisons = num_sets * self.draws_tested
        self.match_percentages = {
            f'{i}_matches': f"{(count/total_comparisons)*100:.2f}%"
            for i, count in self.match_counts.items()
        }