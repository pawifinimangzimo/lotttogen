#!/usr/bin/env python3
import sys
import os
import json
import argparse
from pathlib import Path
import yaml
from typing import List, Tuple
from datetime import datetime
import numpy as np

# Emergency logging that cannot fail
CRASH_LOG = Path('lottery_crash.log')

def emergency_log(error: str):
    try:
        with open(CRASH_LOG, 'a') as f:
            f.write(f"{datetime.now()}: {error}\n")
    except:
        sys.stderr.write(f"EMERGENCY: {error}\n")

# Safe imports
try:
    import logging
    logging_available = True
except ImportError:
    logging_available = False
    emergency_log("Standard logging unavailable")

try:
    from models.config import LotteryConfig
    from models.results import ValidationResult
    from core.data_handler import DataHandler
    from core.analyzer import LotteryAnalyzer
    from core.generator import NumberSetGenerator
    from core.validator import LotteryValidator
except Exception as e:
    emergency_log(f"Import failed: {str(e)}")
    sys.exit(1)

def setup_logging(verbose=False):
    if not logging_available:
        return
    try:
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('lottery_optimizer.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    except Exception as e:
        emergency_log(f"Logging setup failed: {str(e)}")

def parse_args():
    parser = argparse.ArgumentParser(
        description='Lottery Number Generator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--sets', type=int, help='Number of sets to generate')
    parser.add_argument('--mode', choices=['historical', 'none'], default='none')
    return parser.parse_args()

def load_config(config_path: str) -> LotteryConfig:
    try:
        with open(config_path) as f:
            return LotteryConfig(**yaml.safe_load(f))
    except Exception as e:
        emergency_log(f"Config load failed: {str(e)}")
        raise

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def generate_number_sets(generator, num_sets: int) -> List[Tuple[List[int], str]]:
    """Universal set generation that works with both API versions"""
    try:
        # Try modern API first
        if hasattr(generator, 'generate_sets'):
            return generator.generate_sets(num_sets)
        # Fallback to legacy API
        elif hasattr(generator, 'generate_set'):
            return [generator.generate_set() for _ in range(num_sets)]
        else:
            emergency_log("No valid generation method found")
            return []
    except Exception as e:
        emergency_log(f"Generation failed: {str(e)}")
        return []

def save_results(sets: List[Tuple[List[int], str]], output_dir: str) -> bool:
    try:
        output_path = Path(output_dir) / 'suggestions.csv'
        with open(output_path, 'w') as f:
            f.write("numbers,strategy\n")
            for nums, strategy in sets:
                f.write(f"{'-'.join(map(str, nums))},{strategy}\n")
        if logging_available:
            logging.info(f"Saved {len(sets)} sets to {output_path}")
        return True
    except Exception as e:
        emergency_log(f"Save failed: {str(e)}")
        return False

def main():
    args = parse_args()
    setup_logging(args.verbose)
    
    try:
        config = load_config(args.config)
        
        # Initialize components
        data_handler = DataHandler(config)
        data_handler.load_data()
        
        analyzer = LotteryAnalyzer(data_handler.historical, config)
        generator = NumberSetGenerator(analyzer)
        validator = LotteryValidator(data_handler, generator, config)

        # Determine number of sets
        num_sets = args.sets if args.sets is not None else getattr(config.output, 'sets_to_generate', 5)
        
        # Generate number sets
        number_sets = generate_number_sets(generator, num_sets)
        
        if not number_sets:
            emergency_log("No number sets generated")
            sys.exit(1)
            
        if logging_available:
            logging.info(f"Generated {len(number_sets)} number sets")

        # Validation if requested
        if args.mode == 'historical':
            try:
                results = validator.validate_against_historical(number_sets)
                if logging_available:
                    logging.info(f"Validation results: {results.match_counts}")
            except Exception as e:
                emergency_log(f"Validation failed: {str(e)}")

        # Save results
        output_dir = getattr(config.data, 'results_dir', 'results')
        if not save_results(number_sets, output_dir):
            emergency_log("Failed to save results")
            sys.exit(1)

    except Exception as e:
        emergency_log(f"Fatal error: {str(e)}")
        if logging_available:
            logging.critical(str(e), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()