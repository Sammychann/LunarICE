import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui_app import app


def test_app_has_routes():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
