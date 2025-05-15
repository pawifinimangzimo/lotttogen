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
    from models.results import ValidationResult, AnalysisResult
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
        description='Advanced Lottery Number Analyzer and Generator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--config', default='config.yaml',
                      help='Path to configuration file')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose debugging output')
    parser.add_argument('--mode', choices=['analyze', 'generate', 'validate', 'all'],
                      default='all', help='Operation mode')
    parser.add_argument('--draws', type=int,
                      help='Number of draws to analyze')
    parser.add_argument('--sets', type=int, default=10,
                      help='Number of number sets to generate')
    parser.add_argument('--strategy', choices=['hot', 'cold', 'balanced', 'random'],
                      default='balanced', help='Number generation strategy')
    parser.add_argument('--output', help='Output directory for results')
    return parser.parse_args()

def convert_for_json(obj):
    """Convert objects to JSON-serializable formats"""
    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                       np.int16, np.int32, np.int64, np.uint8,
                       np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif hasattr(obj, '__dict__'):
        return {k: convert_for_json(v) for k, v in obj.__dict__.items()}
    return obj

def save_report(data: Dict, file_path: Path) -> bool:
    """Save analysis report to JSON file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(convert_for_json(data), f, indent=2)
        return True
    except Exception as e:
        emergency_log(f"Failed to save report: {str(e)}")
        return False

def analyze_data(analyzer: LotteryAnalyzer, num_draws: Optional[int]) -> AnalysisResult:
    """Perform comprehensive lottery data analysis"""
    try:
        logging.info("Starting data analysis...")
        result = AnalysisResult()
        
        # Basic statistics
        result.basic_stats = analyzer.get_basic_statistics()
        
        # Number frequencies
        result.number_frequencies = analyzer.calculate_frequencies()
        
        # Hot/Cold numbers
        result.hot_numbers = analyzer.get_hot_numbers(num_draws or 50)
        result.cold_numbers = analyzer.get_cold_numbers(num_draws or 100)
        
        # Pattern analysis
        result.common_patterns = analyzer.analyze_patterns()
        
        logging.info("Analysis completed successfully")
        return result
        
    except Exception as e:
        emergency_log(f"Analysis failed: {str(e)}")
        raise

def generate_numbers(generator: NumberSetGenerator, num_sets: int, strategy: str) -> List[Tuple[List[int], str]]:
    """Generate lottery number sets"""
    try:
        logging.info(f"Generating {num_sets} number sets using {strategy} strategy")
        strategies = {
            'hot': generator.generate_hot_sets,
            'cold': generator.generate_cold_sets,
            'balanced': generator.generate_balanced_sets,
            'random': generator.generate_random_sets
        }
        return strategies[strategy](num_sets)
    except Exception as e:
        emergency_log(f"Generation failed: {str(e)}")
        raise

def validate_numbers(validator: LotteryValidator, number_sets: List[Tuple[List[int], str]]]) -> ValidationResult:
    """Validate generated numbers against historical data"""
    try:
        logging.info("Validating number sets...")
        return validator.validate_against_historical(number_sets)
    except Exception as e:
        emergency_log(f"Validation failed: {str(e)}")
        raise

def save_results(results: Dict, output_dir: Path):
    """Save all results to appropriate files"""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save number sets
        if 'generated_sets' in results:
            with open(output_dir / 'generated_sets.csv', 'w') as f:
                f.write("numbers,strategy\n")
                for nums, strategy in results['generated_sets']:
                    f.write(f"{','.join(map(str, nums))},{strategy}\n")
        
        # Save analysis report
        if 'analysis' in results:
            save_report(results['analysis'], output_dir / 'analysis_report.json')
        
        # Save validation report
        if 'validation' in results:
            save_report(results['validation'], output_dir / 'validation_report.json')
        
        logging.info(f"Results saved to {output_dir}")
    except Exception as e:
        emergency_log(f"Failed to save results: {str(e)}")
        raise

def main():
    """Main execution flow with comprehensive error handling"""
    try:
        args = parse_args()
        setup_logging(args.verbose)
        
        try:
            # Load configuration
            config = load_config(args.config)
            
            # Initialize components
            data_handler = DataHandler(config)
            data_handler.load_data()
            
            analyzer = LotteryAnalyzer(data_handler.historical, config)
            generator = NumberSetGenerator(analyzer)
            validator = LotteryValidator(data_handler, generator, config)
            
            results = {}
            
            # Perform requested operations
            if args.mode in ['analyze', 'all']:
                results['analysis'] = analyze_data(analyzer, args.draws)
                
                # Display key findings
                print("\nANALYSIS RESULTS:")
                print(f"Most frequent numbers: {results['analysis'].hot_numbers}")
                print(f"Least frequent numbers: {results['analysis'].cold_numbers}")
            
            if args.mode in ['generate', 'all']:
                results['generated_sets'] = generate_numbers(
                    generator, 
                    args.sets, 
                    args.strategy
                )
                
                # Display generated sets
                print("\nGENERATED NUMBER SETS:")
                for i, (numbers, strategy) in enumerate(results['generated_sets'], 1):
                    print(f"Set {i}: {numbers} ({strategy})")
            
            if args.mode in ['validate', 'all'] and 'generated_sets' in results:
                results['validation'] = validate_numbers(validator, results['generated_sets'])
                
                # Display validation summary
                print("\nVALIDATION RESULTS:")
                print(f"Tested against {len(data_handler.historical)} historical draws")
                print("Match distribution:")
                for matches, count in sorted(results['validation'].match_counts.items()):
                    print(f"{matches} matches: {count}")
            
            # Save all results
            output_dir = Path(args.output or config.data.output_dir or 'results')
            save_results(results, output_dir)
            
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