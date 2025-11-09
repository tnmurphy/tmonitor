from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import sys

# Add the project root directory to the sys path
sys.path.append(str(Path(__file__).absolute().parents[1]))

import main
import database
database.new_test_database(main.app)

class TestMain():

    client = TestClient(main.app)
    def test_endpoint_existence(self):
        """ Check that we see the expected endpoints. """
        app = main.app

        expected_paths = set(["/sense", "/read"])
        paths = set([r.path for r in app.routes if type(r) is APIRoute])
        sd = paths.symmetric_difference(expected_paths)
        print(f"test_force_error: added or removed endpoints: {sd}")
        
        assert len(sd) == 0

    def test_notfound(self):
        r = self.client.post("/blah", json={'bad': 'json'})
        assert r.status_code == 404

    def test_json422(self):
        r = self.client.post("/sense", json={'bad': 'json'})
        assert r.status_code == 422
