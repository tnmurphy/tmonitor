"""
   Test fixtures - common things for all tests.
"""
import sys
from pathlib import Path
import pytest

# Add the project root directory to the sys path so we can 
# import project components
sys.path.append(str(Path(__file__).absolute().parents[1]))
import main 
import database


@pytest.fixture
def database_engine():
    """
     We need a clean database
    """
    database.new_test_database(main.app)

    return main.app.state.engine
