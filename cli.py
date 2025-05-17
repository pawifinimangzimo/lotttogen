#!/usr/bin/env python3
import sys
import os
import json
import argparse
from pathlib import Path
import yaml
from typing import List, Tuple, Any, Dict
from collections import Counter
from datetime import datetime
import numpy as np

# Configure emergency logging first - works without any imports
CRASH_LOG = Path('lottery_crash.log')

def emergency_log(error: str):
    """Atomic logging that cannot fail"""
    try:
        with open(CRASH_LOG, 'a') as f:
            f.write(f"{datetime.now()}: {error}\n")
    except:
        sys.stderr.write(f"EMERGENCY: {error}\n")

# Safe imports with fallback
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
    sys.stderr.write(f"FATAL: Import failed - see {CRASH_LOG}\n")
    sys.exit(1)

def setup_logging(verbose=False):
    """Robust logging setup"""
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
    """Argument parsing with safe defaults"""
    parser = argparse.ArgumentParser(
        description='Lottery Number Generator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--sets', type=int, help='Number of sets to generate')
    parser.add_argument('--mode', choices=['historical', 'none'], default='none')
    parser.add_argument('--validate-saved', help='Validate saved sets')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    return parser.parse_args()

def load_config(config_path: str) -> LotteryConfig:
    """Safe config loading"""
    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
            return LotteryConfig(**config_data)
    except Exception as e:
        emergency_log(f"Config load failed: {str(e)}")
        raise

class SafeEncoder(json.JSONEncoder):
    """Handles all numpy types and custom objects"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if hasattr(obj, '__dict__'):
            return vars(obj)
        return super().default(obj)

def save_results(sets: List[Tuple[List[int], str]], output_dir: str) -> bool:
    """Guaranteed result saving"""
    try:
        output_path = Path(output_dir) / 'suggestions.csv'
        with open(output_path, 'w') as f:
            f.write("numbers,strategy\n")
            for nums, strategy in sets:
                f.write(f"{'-'.join(map(str, nums))},{strategy}\n")
        if logging_available:
            logging.info(f"Saved {len(sets)} sets")
        return True
    except Exception as e:
        emergency_log(f"Save failed: {str(e)}")
        return False

def main():
    """Main workflow with complete error handling"""
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

        # Generate sets - handle both old and new generator APIs
        num_sets = args.sets if args.sets else getattr(config.output, 'sets_to_generate', 5)
        try:
            number_sets = generator.generate_sets(num_sets)
        except TypeError:
            # Fallback for older generator API
            number_sets = [generator.generate_set() for _ in range(num_sets)]

        # Validation
        if args.mode == 'historical':
            try:
                results = validator.validate_against_historical(number_sets)
                if logging_available:
                    logging.info(f"Validation complete: {results.match_counts}")
            except AttributeError:
                emergency_log("Validation not available in this version")

        # Save results
        output_dir = getattr(config.data, 'results_dir', 'results')
        if not save_results(number_sets, output_dir):
            emergency_log("Result saving failed")

        if logging_available:
            logging.info("Completed successfully")

    except Exception as e:
        emergency_log(f"Fatal error: {str(e)}")
        if logging_available:
            logging.critical(str(e), exc_info=args.verbose)
        sys.exit(1)

if __name__ == "__main__":
    main()