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

[... rest of your existing functions remain unchanged ...]

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