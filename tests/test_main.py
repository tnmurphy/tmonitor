from fastapi import Request, HTTPException
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import sys

# Add the project root directory to the sys path
sys.path.append(str(Path(__file__).absolute().parents[1]))

import main
import database


def create_failing_endpoint(app):
    @app.get("/testexception", response_class=JSONResponse)
    def test_exception(request: Request):
        """
           Throws an exception. Check that works.  Currently this DOES NOT
           work with anything that's not derived from HTTPException in
           the sense that such exceptions get both handled and somehow
           reraised.
        """
        request.state.logger.info("/testexception")
        raise HTTPException(500, "This should be caught by the generic handler")
        return JSONResponse({}, status_code=200)

    return


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

    def test_generic_exception(self, database_engine):
        create_failing_endpoint(main.app)
        r = self.client.get("/testexception")
        assert r.status_code == 500

