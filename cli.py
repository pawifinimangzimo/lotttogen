#!/usr/bin/env python3
import sys
import os
import json
import argparse
from pathlib import Path
import yaml
from typing import List, Tuple, Any, Dict, Optional
from collections import Counter
from datetime import datetime

# Configure emergency logging first
CRASH_LOG = Path('lottery_crash.log')
SUCCESS_LOG = Path('lottery_optimizer.log')

def emergency_log(error: str):
    """Atomic error logging that cannot fail"""
    try:
        with open(CRASH_LOG, 'a') as f:
            f.write(f"{datetime.now()}: {error}\n")
    except:
        os.write(2, f"CRASH LOG FAILED: {error}\n".encode())

def safe_print(*args, **kwargs):
    """Print that works during interpreter shutdown"""
    try:
        print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except:
        emergency_log("Print failed: " + " ".join(str(a) for a in args))

# Safe imports with fallback
try:
    import logging
    import numpy as np
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
        if 'logging' not in globals():
            raise RuntimeError("Logging module not available")
            
        level = logging.DEBUG if verbose else logging.INFO
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        handlers = [
            logging.FileHandler(SUCCESS_LOG),
            logging.StreamHandler(sys.stdout)
        ]
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
    except Exception as e:
        emergency_log(f"Logging setup failed: {str(e)}")
        safe_print("WARNING: Logging partially failed - see", CRASH_LOG)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Lottery Number Analyzer',
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

def validation_result_to_dict(result: ValidationResult) -> Dict:
    """Convert ValidationResult to serializable dictionary"""
    return {
        'draws_tested': result.draws_tested,
        'match_counts': dict(result.match_counts),
        'match_percentages': dict(result.match_percentages),
        'best_per_draw': list(result.best_per_draw) if result.best_per_draw else None
    }

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

def get_report_path(config) -> Path:
    """Safe path resolution for reports"""
    try:
        # Check for report_path in validation config
        if hasattr(config.validation, 'report_path'):
            return Path(config.validation.report_path)
        # Fallback to results directory
        if hasattr(config.data, 'results_dir'):
            return Path(config.data.results_dir)
    except Exception:
        pass
    # Final fallback to current directory
    return Path.cwd()

def save_validation_report(validation_results: ValidationResult, 
                         number_sets: List[Tuple[List[int], str]], 
                         config) -> bool:
    """Save validation report with proper serialization"""
    try:
        report_dir = get_report_path(config)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / 'validation_report.json'
        
        report_data = {
            'historical': validation_result_to_dict(validation_results),
            'sets': number_sets
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        logging.info(f"Saved validation report to {report_path}")
        return True
    except Exception as e:
        emergency_log(f"Failed to save validation report: {str(e)}")
        logging.error(f"Failed to save validation report: {str(e)}")
        return False

def main():
    """Main execution flow with robust error handling"""
    try:
        args = parse_args()
        setup_logging(args.verbose)
        
        try:
            config = load_config(args.config)
            
            # Apply CLI overrides
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
                if hasattr(validator, 'analyze_latest_draw'):
                    validator.analyze_latest_draw()
                elif data_handler.latest_draw is not None:
                    analyzer.analyze_draw(data_handler.latest_draw)
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
                
                if hasattr(config.validation, 'save_report') and config.validation.save_report:
                    if not save_validation_report(validation_results, number_sets, config):
                        logging.warning("Failed to save validation report")

            # Save final results
            if not save_results(number_sets, config.data.results_dir):
                logging.warning("Failed to save some results")

        except Exception as e:
            try:
                logging.critical(f"Runtime error: {str(e)}", exc_info=args.verbose)
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