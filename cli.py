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

# Configure emergency logging first
CRASH_LOG = Path('lottery_crash.log')
SUCCESS_LOG = Path('lottery_optimizer.log')

def emergency_log(error: str):
    try:
        with open(CRASH_LOG, 'a') as f:
            f.write(f"{datetime.now()}: {error}\n")
    except:
        os.write(2, f"CRASH LOG FAILED: {error}\n".encode())

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except:
        emergency_log("Print failed: " + " ".join(str(a) for a in args))

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

try:
    import logging
    from models.config import LotteryConfig
    from models.results import ValidationResult
    from core.data_handler import DataHandler
    from core.analyzer import LotteryAnalyzer
    from core.generator import NumberSetGenerator
    from core.validator import LotteryValidator
except Exception as e:
    emergency_log(f"Import failed: {str(e)}")
    safe_print("FATAL: Module import failed - see", CRASH_LOG)
    sys.exit(1)

def setup_logging(verbose=False):
    try:
        level = logging.DEBUG if verbose else logging.INFO
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handlers = [
            logging.FileHandler(SUCCESS_LOG),
            logging.StreamHandler(sys.stdout)
        ]
        logging.basicConfig(level=level, format=formatter.format, handlers=handlers)
    except Exception as e:
        emergency_log(f"Logging setup failed: {str(e)}")
        safe_print("WARNING: Logging partially failed - see", CRASH_LOG)

def parse_args():
    parser = argparse.ArgumentParser(description='Lottery Number Generator')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--sets', type=int, help='Override number of sets to generate')
    parser.add_argument('--mode', choices=['historical', 'new_draw', 'both', 'none'], 
                      default='none', help='Validation mode')
    parser.add_argument('--validate-saved', help='Validate saved number sets')
    parser.add_argument('--analyze-latest', action='store_true', help='Analyze latest draw')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--match-threshold', type=int, help='Match threshold')
    parser.add_argument('--show-top', type=int, help='Number of top results to show')
    return parser.parse_args()

def load_config(config_path: str) -> LotteryConfig:
    try:
        with open(config_path) as f:
            return LotteryConfig(**yaml.safe_load(f))
    except Exception as e:
        emergency_log(f"Config load failed: {str(e)}")
        safe_print(f"ERROR: Failed to load config: {str(e)}")
        raise

def save_results(sets: List[Tuple[List[int], str]], output_dir: str) -> bool:
    try:
        output_path = Path(output_dir) / 'suggestions.csv'
        with open(output_path, 'w') as f:
            f.write("numbers,strategy\n")
            for nums, strategy in sets:
                f.write(f"{'-'.join(map(str, nums))},{strategy}\n")
        logging.info(f"Saved {len(sets)} sets to {output_path}")
        return True
    except Exception as e:
        emergency_log(f"Save failed: {str(e)}")
        logging.error(f"Failed to save results: {str(e)}")
        return False

def main():
    try:
        args = parse_args()
        setup_logging(args.verbose)
        
        try:
            config = load_config(args.config)
            
            # Determine number of sets (CLI overrides config)
            num_sets = args.sets if args.sets is not None else config.output.sets_to_generate
            logging.info(f"Generating {num_sets} number sets")
            
            data_handler = DataHandler(config)
            data_handler.load_data()
            
            analyzer = LotteryAnalyzer(data_handler.historical, config)
            generator = NumberSetGenerator(analyzer)
            validator = LotteryValidator(data_handler, generator, config)
            
            # Generate the specified number of sets
            number_sets = generator.generate_sets(num_sets)
            
            if len(number_sets) < num_sets:
                logging.warning(f"Generated {len(number_sets)}/{num_sets} sets (strategy constraints may limit output)")
            
            if args.analyze_latest and data_handler.latest_draw:
                validator.analyze_latest_draw()
            
            if args.stats:
                analyzer.generate_statistics_report()
            
            if args.validate_saved:
                validator.validate_saved_sets(args.validate_saved)
            elif args.mode != 'none':
                validation_results = validator.validate_against_historical(number_sets)
                if config.output.verbose:
                    print(f"\nValidation Results (Tested against {validation_results.draws_tested} draws):")
                    for i in range(7):
                        print(f"{i} matches: {validation_results.match_counts.get(i, 0)}")
            
            if not save_results(number_sets, config.data.results_dir):
                logging.warning("Failed to save some results")
                
            logging.info(f"Successfully generated {len(number_sets)} number sets")
            
        except Exception as e:
            logging.critical(f"Runtime error: {str(e)}", exc_info=args.verbose)
            raise
            
    except Exception as e:
        emergency_log(f"Fatal error: {str(e)}")
        safe_print(f"CRITICAL ERROR: {str(e)}\nSee {CRASH_LOG} for details")
        sys.exit(1)

if __name__ == "__main__":
    main()