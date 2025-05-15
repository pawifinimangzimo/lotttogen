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
    
def convert_numpy_types(obj: Any) -> Any:
    """Recursively convert numpy types to native Python types"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj