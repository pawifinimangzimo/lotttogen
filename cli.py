#!/usr/bin/env python3
import logging
import argparse
import sys
from pathlib import Path
import yaml
import json
from typing import Optional, List, Dict, Tuple
from collections import Counter

from models.config import LotteryConfig
from models.results import ValidationResult
from core.data_handler import DataHandler
from core.analyzer import LotteryAnalyzer
from core.generator import NumberSetGenerator
from core.validator import LotteryValidator

# Global reference to prevent handler garbage collection
_logging_handlers = None

def _setup_logging(verbose=False):
    """Configure logging system with shutdown protection"""
    global _logging_handlers
    
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Create and store handlers
    _logging_handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('lottery_optimizer.log')
    ]
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    for handler in _logging_handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

def _handle_critical_error(error, verbose=False):
    """Last-resort error handling that never fails"""
    error_msg = f"""
    {'*' * 80}
    CRITICAL ERROR: {str(error)}
    {'*' * 80}
    """
    
    # Try normal logging first
    try:
        if 'logging' in globals():
            logging.critical(error_msg, exc_info=verbose)
            return
    except Exception:
        pass
    
    # Fallback to direct stderr writing
    sys.stderr.write(error_msg)
    sys.stderr.flush()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Adaptive Lottery Number Optimizer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--config', default='config.yaml',
                      help='Path to configuration file')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose debugging output')
    parser.add_argument('--mode', choices=['historical', 'new_draw', 'both', 'none'],
                      default='none', help='Validation mode to run')
    parser.add_argument('--validate-saved', metavar='PATH',
                      help='Validate saved number sets from CSV file')
    parser.add_argument('--analyze-latest', action='store_true',
                      help='Show detailed analysis of latest draw')
    parser.add_argument('--stats', action='store_true',
                      help='Show advanced statistics')
    parser.add_argument('--match-threshold', type=int,
                      help='Minimum matches to show in validation')
    parser.add_argument('--show-top', type=int,
                      help='Number of top results to display')
    return parser.parse_args()

def load_config(config_path: str) -> LotteryConfig:
    """Load and validate configuration"""
    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        return LotteryConfig(**config_data)
    except Exception as e:
        _handle_critical_error(f"Failed to load config: {str(e)}")
        raise

def print_validation_results(results: ValidationResult) -> None:
    """Display validation results in readable format"""
    print("\nVALIDATION RESULTS:")
    print(f"Tested against {results.draws_tested} historical draws")
    print("Match distribution:")
    for i in range(7):
        print(f"{i} matches: {results.match_counts.get(i, 0)} "
              f"({results.match_percentages.get(f'{i}_matches', '0%')})")
    
    if results.best_per_draw:
        print(f"\nBest match per draw: {Counter(results.best_per_draw)}")

def save_results(sets: List[Tuple[List[int], str]], output_dir: str) -> bool:
    """Save generated number sets to CSV"""
    try:
        output_path = Path(output_dir) / 'suggestions.csv'
        with open(output_path, 'w') as f:
            f.write("numbers,strategy\n")
            for nums, strategy in sets:
                f.write(f"{'-'.join(map(str, nums))},{strategy}\n")
        logging.info(f"Saved results to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save results: {str(e)}")
        return False

def main():
    """Main execution flow with robust error handling"""
    args = parse_args()
    
    try:
        # Setup protected logging
        _setup_logging(args.verbose)
        
        # Load configuration
        config = load_config(args.config)
        
        # Override config with CLI args if provided
        if args.match_threshold:
            config.analysis.default_match_threshold = args.match_threshold
        if args.show_top:
            config.analysis.default_show_top = args.show_top
        if args.verbose:
            config.output.verbose = True

        # Initialize components
        data_handler = DataHandler(config)
        data_handler.prepare_filesystem()
        data_handler.load_data()
        
        analyzer = LotteryAnalyzer(data_handler.historical, config)
        generator = NumberSetGenerator(analyzer)
        validator = LotteryValidator(data_handler, generator, config)

        # Generate number sets
        number_sets = generator.generate_sets()
        
        # Handle analysis modes
        if args.analyze_latest:
            if data_handler.latest_draw is not None:
                validator.analyze_latest_draw()
            else:
                logging.warning("No latest draw available for analysis")
        
        if args.stats:
            analyzer.generate_statistics_report()
        
        # Handle validation modes
        if args.validate_saved:
            validator.validate_saved_sets(args.validate_saved)
        elif args.mode != 'none':
            validation_results = validator.validate_against_historical(number_sets)
            if config.output.verbose:
                print_validation_results(validation_results)
            
            if config.validation.save_report:
                validator.save_validation_report({
                    'historical': validation_results,
                    'sets': number_sets
                })

        # Save final results
        if not save_results(number_sets, config.data.results_dir):
            logging.warning("Failed to save some results")

    except Exception as e:
        _handle_critical_error(e, args.verbose)
        sys.exit(1)

if __name__ == "__main__":
    main()