#!/usr/bin/env python3
import sys
import os
import json
import argparse
from pathlib import Path
import yaml
from typing import List, Tuple, Any, Dict
from collections import Counter

# Emergency logging system
CRASH_LOG = Path('lottery_crash.log')
SUCCESS_LOG = Path('lottery_optimizer.log')

def emergency_log(error: str):
    """Atomic error logging that cannot fail"""
    try:
        with open(CRASH_LOG, 'a') as f:
            f.write(f"{os.getpid()}: {error}\n")
    except:
        os.write(2, f"CRASH LOG FAILED: {error}\n".encode())

def safe_print(*args, **kwargs):
    """Print that works during interpreter shutdown"""
    try:
        print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except:
        emergency_log("Print failed: " + " ".join(str(a) for a in args))

def convert_for_json(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable types"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return convert_for_json(obj.__dict__)
    else:
        return str(obj)

# Safe imports with fallback
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
    """Configure logging system with crash protection"""
    try:
        level = logging.DEBUG if verbose else logging.INFO
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = logging.FileHandler(SUCCESS_LOG)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        
        logger = logging.getLogger()
        logger.setLevel(level)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    except Exception as e:
        emergency_log(f"Logging setup failed: {str(e)}")
        safe_print("WARNING: Logging partially failed - see", CRASH_LOG)

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
        emergency_log(f"Config load failed: {str(e)}")
        safe_print(f"ERROR: Failed to load config: {str(e)}")
        raise

def print_validation_results(results: ValidationResult) -> None:
    """Display validation results"""
    try:
        print("\nVALIDATION RESULTS:")
        print(f"Tested against {results.draws_tested} historical draws")
        print("Match distribution:")
        for i in range(7):
            print(f"{i} matches: {results.match_counts.get(i, 0)} "
                  f"({results.match_percentages.get(f'{i}_matches', '0%')})")
        
        if results.best_per_draw:
            print(f"\nBest match per draw: {Counter(results.best_per_draw)}")
    except Exception as e:
        emergency_log(f"Results print failed: {str(e)}")

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
        emergency_log(f"Save failed: {str(e)}")
        safe_print(f"ERROR: Failed to save results: {str(e)}")
        return False

def save_validation_report(data: Dict, file_path: str) -> bool:
    """Safely save validation report with JSON serialization"""
    try:
        with open(file_path, 'w') as f:
            json.dump(convert_for_json(data), f, indent=2)
        return True
    except Exception as e:
        emergency_log(f"Validation report save failed: {str(e)}")
        safe_print(f"ERROR: Failed to save validation report: {str(e)}")
        return False

def main():
    """Main execution flow with robust error handling"""
    try:
        args = parse_args()
        setup_logging(args.verbose)
        
        try:
            config = load_config(args.config)
            
            if args.match_threshold:
                config.analysis.default_match_threshold = args.match_threshold
            if args.show_top:
                config.analysis.default_show_top = args.show_top
            if args.verbose:
                config.output.verbose = True

            data_handler = DataHandler(config)
            data_handler.prepare_filesystem()
            data_handler.load_data()
            
            analyzer = LotteryAnalyzer(data_handler.historical, config)
            generator = NumberSetGenerator(analyzer)
            validator = LotteryValidator(data_handler, generator, config)

            number_sets = generator.generate_sets()
            
            if args.analyze_latest:
                if data_handler.latest_draw is not None:
                    validator.analyze_latest_draw()
                else:
                    logging.warning("No latest draw available for analysis")
            
            if args.stats:
                analyzer.generate_statistics_report()
            
            if args.validate_saved:
                validator.validate_saved_sets(args.validate_saved)
            elif args.mode != 'none':
                validation_results = validator.validate_against_historical(number_sets)
                if config.output.verbose:
                    print_validation_results(validation_results)
                
                if config.validation.save_report:
                    report_data = {
                        'historical': validation_results,
                        'sets': number_sets
                    }
                    if not save_validation_report(report_data, 
                                               Path(config.validation.report_path) / 'validation_report.json'):
                        logging.error("Failed to save validation report")

            if not save_results(number_sets, config.data.results_dir):
                logging.warning("Failed to save some results")

        except Exception as e:
            try:
                logging.critical(f"Runtime error: {str(e)}", exc_info=True)
            except:
                emergency_log(f"Runtime error (logging failed): {str(e)}")
            raise
            
    except Exception as fatal_error:
        emergency_log(f"Fatal: {str(fatal_error)}")
        safe_print(f"""
        {'!' * 60}
        CRITICAL ERROR (Report saved to {CRASH_LOG})
        {str(fatal_error)}
        {'!' * 60}
        """)
        sys.exit(1)

if __name__ == "__main__":
    main()