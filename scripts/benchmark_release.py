#!/usr/bin/env python3
"""M7.2 — Indicative query-count baselines for key learner pages.

Not a production SLA: measures SQL statements on a fresh, seeded SQLite
database in a test app context. Re-run after material changes:

    .venv/bin/python scripts/benchmark_release.py
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sqlalchemy  # noqa: E402

QUERY_COUNT = {'n': 0}


def count_queries(conn, cursor, statement, parameters, context, executemany):
    QUERY_COUNT['n'] += 1


def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['DATABASE_URL'] = f'sqlite:///{tmp}/bench.db'
        os.environ.setdefault('SECRET_KEY', 'bench-only')
        os.environ.setdefault('APP_ENV', 'testing')
        from app import create_app, db  # noqa: E402
        app = create_app()
        app.config.update(TESTING=True, GEMINI_API_KEY=None)

        with app.app_context():
            db.create_all()
            from werkzeug.security import generate_password_hash
            user = db.session.execute(db.text(
                "INSERT INTO user (username, email, password_hash, public_id) "
                "VALUES ('bench', 'bench@example.test', :p, 'RU-BENCH01')"
            ), {'p': generate_password_hash('x')})
            db.session.commit()

        with app.app_context():
            sqlalchemy.event.listens_for(db.engine, 'before_cursor_execute')(count_queries)
            urls = [
                '/',                      # dashboard
                '/lessons',               # lesson catalogue
                '/passport',              # skill passport
                '/arena/machine-learning',  # arena catalogue
                '/mastery',               # learning intelligence
            ]
            for url in urls:
                client = app.test_client()
                client.post('/login', data={'username': 'bench', 'password': 'x'}, follow_redirects=True)
                QUERY_COUNT['n'] = 0
                response = client.get(url)
                print(f'{url:24s} status={response.status_code} queries={QUERY_COUNT["n"]}')


if __name__ == '__main__':
    main()
