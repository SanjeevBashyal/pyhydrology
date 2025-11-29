
import sys
from pathlib import Path
import typing

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from pySWATPlus import Calibration
    import pySWATPlus.validators as validators
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

print("Successfully imported Calibration")

try:
    hints = typing.get_type_hints(Calibration.__init__)
    print("Type hints retrieved successfully")
    for k, v in hints.items():
        print(f"{k}: {v}")
except Exception as e:
    print(f"Error getting type hints: {e}")
    sys.exit(1)

print("\nTesting validation logic manually...")

# Mock values
locals_dict = {
    'self': None,
    'parameters': [],
    'calsim_dir': Path('.'),
    'txtinout_dir': Path('.'),
    'extract_data': {},
    'observe_data': {},
    'objective_config': {},
    'algorithm': 'NSGA2',
    'n_gen': 10,
    'pop_size': 10,
    'max_workers': None
}

try:
    validators._variable_origin_static_type(hints, locals_dict)
    print("Validation successful")
except TypeError as e:
    print(f"Validation failed with TypeError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Validation failed with {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
