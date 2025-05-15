#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import argparse
import yaml
from typing import List, Tuple
from collections import Counter

# Constants
CRASH_LOG = Path('lottery_crash.log')
SUCCESS_LOG = Path('lottery_optimizer.log')

def write_crash_log(error: str):
    """Atomic error logging that cannot fail"""
    try:
        with open(CRASH_LOG, 'a') as f:
            f.write(f"{os.getpid()}: {error}\n")
    except:
        # Absolute last resort
        os.write(2, f"CRASH LOG FAILED: {error}\n".encode())

def safe_print(*args, **kwargs):
    """Print that can't fail during interpreter shutdown"""
    try:
        print(*args, **kwargs)
    except:
        write_crash_log("Print failed: " + " ".join(str(a) for a in args))

# Now safely import other modules
try:
    import logging
    from models.config import LotteryConfig
    from models.results import ValidationResult
    from core.data_handler import DataHandler
    from core.analyzer import LotteryAnalyzer
    from core.generator import NumberSetGenerator
    from core.validator import LotteryValidator
except Exception as e:
    write_crash_log(f"Import failed: {str(e)}")
    safe_print("FATAL: Module import failed - see", CRASH_LOG)
    sys.exit(1)

def setup_logging(verbose=False):
    """Configure logging with isolated file handler"""
    try:
        level = logging.DEBUG if verbose else logging.INFO
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler (separate from crash log)
        file_handler = logging.FileHandler(SUCCESS_LOG)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Stream handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(level)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    except Exception as e:
        write_crash_log(f"Logging setup failed: {str(e)}")
        safe_print("WARNING: Logging partially failed - see", CRASH_LOG)



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
    """Main entry point with guaranteed error reporting"""
    try:
        args = parse_args()
        setup_logging(args.verbose)
        
        try:
            # [Rest of your main logic]
        except Exception as e:
            safe_print(f"\nERROR: {str(e)}\n")
            write_crash_log(f"Runtime error: {str(e)}")
            raise
            
    except Exception as fatal_error:
        # Last-ditch effort to record failure
        write_crash_log(f"Fatal: {str(fatal_error)}")
        safe_print(f"""
        {'!' * 60}
        CRITICAL ERROR (Report saved to {CRASH_LOG})
        {str(fatal_error)}
        {'!' * 60}
        """)
        sys.exit(1)

if __name__ == "__main__":
    main()