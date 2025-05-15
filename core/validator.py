from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
import json
from tabulate import tabulate
from models.config import LotteryConfig
from models.results import ValidationResult
from utils.helpers import convert_numpy_types

class LotteryValidator:
    def __init__(self, data_handler, generator, config: LotteryConfig):
        self.data_handler = data_handler
        self.generator = generator
        self.config = config

    def validate_against_historical(self, sets: List) -> ValidationResult:
        """Validate generated sets against historical data"""
        test_draws = min(
            self.config.validation.test_draws,
            len(self.data_handler.historical)-1
        )
        test_data = self.data_handler.historical.iloc[-test_draws-1:-1]
        
        result = ValidationResult(draws_tested=len(test_data))
        
        for _, draw in test_data.iterrows():
            target = set(draw[self.generator.analyzer.number_cols])
            best_match = 0
            
            for generated_set, _ in sets:
                matches = len(set(generated_set) & target)
                result.match_counts[matches] += 1
                best_match = max(best_match, matches)
                
                if matches >= self.config.validation.alert_threshold:
                    result.high_performance_sets.append(generated_set)
            
            result.best_per_draw.append(best_match)
        
        result.calculate_percentages(len(sets))
        return result

    def validate_against_latest(self, sets: List) -> Optional[Dict]:
        """Validate against the latest draw if available"""
        if self.data_handler.latest_draw is None:
            return None
            
        target = set(self.data_handler.latest_draw[
            self.generator.analyzer.number_cols
        ])
        
        results = {
            'draw_date': self.data_handler.latest_draw['date'].strftime('%m/%d/%y'),
            'draw_numbers': sorted([int(n) for n in target]),
            'sets': []
        }

        for generated_set, strategy in sets:
            matches = len(set(generated_set) & target)
            results['sets'].append({
                'numbers': [int(n) for n in generated_set],
                'strategy': strategy,
                'matches': matches,
                'matched_numbers': sorted([int(n) for n in set(generated_set) & target])
            })

        return results

    def save_validation_report(self, results):
        try:
            report_path = Path(self.config.data.stats_dir) / 'validation_report.json'
            with open(report_path, 'w') as f:
                json.dump(convert_numpy_types(results), f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving validation report: {str(e)}")
            return False

    def _convert_results(self, results):
        """Convert results to JSON-serializable format"""
        if isinstance(results, dict):
            return {k: self._convert_results(v) for k, v in results.items()}
        elif isinstance(results, list):
            return [self._convert_results(item) for item in results]
        elif hasattr(results, 'dict'):
            return results.dict()
        return results