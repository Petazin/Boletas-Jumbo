import sys
import os
import pytest

@pytest.fixture(scope='session', autouse=True)
def add_project_root_to_path():
    print("\n--- conftest.py: add_project_root_to_path fixture started ---")
    original_sys_path = list(sys.path) # Make a copy to compare later

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"Project root calculated: {project_root}")

    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added project root to sys.path. New sys.path[0]: {sys.path[0]}")
    else:
        print("Project root already in sys.path.")

    print("Current sys.path:")
    for p in sys.path:
        print(f"  - {p}")
    print("--- conftest.py: add_project_root_to_path fixture finished ---\n")