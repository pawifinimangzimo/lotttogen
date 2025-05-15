import argparse
from pathlib import Path
import yaml
from typing import Optional

from models.config import LotteryConfig
from core.data_handler import DataHandler
from core.analyzer import LotteryAnalyzer
from core.generator import NumberSetGenerator
from core.validator import LotteryValidator

def main():
    args = parse_args()
    config = load_config(args.config)
    
    try:
        # Initialize components
        data_handler = DataHandler(config)
        data_handler.prepare_filesystem()
        data_handler.load_data()
        
        analyzer = LotteryAnalyzer(data_handler.historical, config)
        generator = NumberSetGenerator(analyzer)
        validator = LotteryValidator(data_handler, generator, config)

        # Generate number sets
        number_sets = generator.generate_sets()
        
        # Run validation if configured
        if config.validation.mode != 'none':
            validation_results = validator.validate_against_historical(number_sets)
            
            if config.output.verbose:
                print_validation_results(validation_results)
                
            if config.validation.save_report:
                validator.save_validation_report({
                    'historical': validation_results,
                    'sets': number_sets
                })

        # Save results
        save_results(number_sets, config.data.results_dir)

    except Exception as e:
        print(f"Error: {str(e)}")
        if config.output.verbose:
            import traceback
            traceback.print_exc()

def parse_args():
    parser = argparse.ArgumentParser(description='Lottery Number Optimizer')
    parser.add_argument('--config', default='config.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    return parser.parse_args()

def load_config(config_path: str) -> LotteryConfig:
    """Load and validate configuration"""
    with open(config_path) as f:
        config_data = yaml.safe_load(f)
    
    return LotteryConfig(**config_data)

def print_validation_results(results: ValidationResult) -> None:
    """Print validation results in readable format"""
    print("\nVALIDATION RESULTS:")
    print(f"Tested against {results.draws_tested} historical draws")
    print("Match distribution:")
    for i in range(7):
        print(f"{i} matches: {results.match_counts.get(i, 0)} ({results.match_percentages.get(f'{i}_matches', '0%')})")
    
    print(f"\nBest match per draw: {collections.Counter(results.best_per_draw)}")

def save_results(sets: List, output_dir: str) -> bool:
    """Save generated sets to CSV"""
    try:
        output_path = Path(output_dir) / 'suggestions.csv'
        with open(output_path, 'w') as f:
            f.write("numbers,strategy\n")
            for nums, strategy in sets:
                f.write(f"{'-'.join(map(str, nums))},{strategy}\n")
        return True
    except Exception as e:
        print(f"Error saving results: {str(e)}")
        return False

if __name__ == "__main__":
    main()