import importlib
import types


def get_app():
    app_module = importlib.import_module('app')
    return getattr(app_module, 'app')


def test_help_route_returns_200():
    app = get_app()
    app.testing = True
    with app.test_client() as client:
        resp = client.get('/help')
        assert resp.status_code == 200
        assert b"Help" in resp.data or len(resp.data) > 0 