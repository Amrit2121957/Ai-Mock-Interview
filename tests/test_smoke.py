import sys
from pathlib import Path
import importlib
import types

# Ensure repo root is on sys.path for CI environments
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))


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