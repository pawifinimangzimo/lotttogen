from typing import List
from pathlib import Path

def save_json(data: dict, path: Path) -> bool:
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Failed to save JSON: {e}")
        return False

def validate_numbers(numbers: List[int], pool_size: int) -> bool:
    return all(1 <= n <= pool_size for n in numbers)