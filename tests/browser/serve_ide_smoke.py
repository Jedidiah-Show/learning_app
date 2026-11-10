"""Serve a clean-database Flask app and the real IDE browser smoke page."""
from pathlib import Path
import os
import sys
import tempfile

from flask import send_from_directory

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

temporary_database = tempfile.TemporaryDirectory(prefix='ruach-browser-')
os.environ['DATABASE_URL'] = f"sqlite:///{Path(temporary_database.name) / 'browser.db'}"
os.environ['APP_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'browser-test-only-secret'
os.environ['GEMINI_API_KEY'] = ''
os.environ['OPENROUTER_API_KEY'] = ''

from app import create_app, db

app = create_app()
app.config.update(TESTING=True, CSRF_ENABLED=True)
with app.app_context():
    db.create_all()


@app.get('/tests/browser/ide-smoke.html')
def ide_smoke_page():
    return send_from_directory(ROOT / 'tests' / 'browser', 'ide-smoke.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4173, threaded=True, use_reloader=False)
