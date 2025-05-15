#!/usr/bin/env python3
import logging
import argparse
import sys
from pathlib import Path
import yaml
import json
from typing import Optional, List, Dict, Tuple
from collections import Counter  # Needed for the Counter output

from models.config import LotteryConfig
from models.results import ValidationResult
from core.data_handler import DataHandler
from core.analyzer import LotteryAnalyzer
from core.generator import NumberSetGenerator
from core.validator import LotteryValidator

def setup_logging(verbose=False):
    """Configure logging system"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('lottery_optimizer.log')
        ]
    )
    
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
        logging.error(f"Failed to load config: {str(e)}")
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
        from collections import Counter
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
        """Main execution flow with bulletproof error handling"""
        args = parse_args()
        
        # 1. Setup logging with strong references
        _setup_logging_with_protection(args.verbose)
        
        try:
            # [Your existing main code here]
            
        except Exception as e:
            # 2. Ultra-robust error reporting
            _handle_critical_error(e, args.verbose)
            sys.exit(1)

    def _setup_logging_with_protection(verbose=False):
        """Configure logging that survives interpreter shutdown"""
        global _logging_handlers  # Strong reference to prevent GC
        
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

    def _handle_critical_error(error, verbose):
        """Last-resort error handling that never fails"""
        try:
            # First try proper logging
            if 'logging' in globals():
                logging.critical(f"Fatal error: {error}", exc_info=verbose)
        except:
            pass
        
        # Guaranteed fallback output
        error_msg = f"""
        {'*' * 80}
        CRITICAL ERROR (logging unavailable):
        {str(error)}
        {'*' * 80}
        """
        sys.stderr.write(error_msg)
        sys.stderr.flush()

if __name__ == "__main__":
    main()