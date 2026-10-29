import unittest

from app import _normalize_database_url


class DatabaseUrlTests(unittest.TestCase):
    def test_postgres_url_uses_psycopg_and_adds_tls_in_production(self):
        self.assertEqual(
            _normalize_database_url(
                'postgres://user:pass@db.example.com/app', production=True
            ),
            'postgresql+psycopg://user:pass@db.example.com/app?sslmode=require',
        )

    def test_existing_sslmode_is_not_overridden(self):
        self.assertEqual(
            _normalize_database_url(
                'postgresql://user:pass@db.example.com/app?sslmode=verify-full',
                production=True,
            ),
            'postgresql+psycopg://user:pass@db.example.com/app?sslmode=verify-full',
        )

    def test_localhost_is_not_forced_to_tls(self):
        self.assertEqual(
            _normalize_database_url(
                'postgresql://user:pass@localhost/app', production=True
            ),
            'postgresql+psycopg://user:pass@localhost/app',
        )


if __name__ == '__main__':
    unittest.main()
