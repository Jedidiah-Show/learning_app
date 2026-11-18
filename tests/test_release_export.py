"""Release source export tests (M0.1 / M0.5).

Runs the real exporter against the repository and verifies the archive
contains committed source only, plus manifest and checksum.
"""

import hashlib
import os
import shutil
import tarfile
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_SCRIPT = os.path.join(REPO_ROOT, 'scripts', 'export_release_source.sh')


@unittest.skipUnless(shutil.which('git'), 'git is required')
class ReleaseExportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_produces_clean_archive_with_manifest_and_checksum(self):
        import subprocess
        result = subprocess.run(
            ['bash', EXPORT_SCRIPT, self.temp_dir.name, '--allow-dirty'],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=600,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        archives = [f for f in os.listdir(self.temp_dir.name) if f.endswith('.tar.gz')]
        self.assertEqual(len(archives), 1)
        archive = os.path.join(self.temp_dir.name, archives[0])

        # Checksum matches the archive.
        with open(archive + '.sha256') as handle:
            recorded = handle.read().split()[0]
        with open(archive, 'rb') as handle:
            actual = hashlib.sha256(handle.read()).hexdigest()
        self.assertEqual(recorded, actual)

        # Manifest exists and lists files.
        with open(os.path.join(self.temp_dir.name, 'MANIFEST.txt')) as handle:
            manifest = handle.read()
        self.assertIn('git_commit:', manifest)
        self.assertIn('file_count:', manifest)

        # Archive contains no prohibited files.
        with tarfile.open(archive) as tar:
            names = tar.getnames()
        self.assertTrue(names)
        for name in names:
            lowered = name.lower()
            if lowered.endswith('.env.example'):
                continue
            self.assertNotIn('/.env', lowered)
            self.assertNotIn('client_secret', lowered)
            self.assertNotIn('node_modules', lowered)
            self.assertNotIn('.venv', lowered)
            self.assertNotIn('instance/', lowered)
            self.assertNotRegex(lowered, r'\.(db|sqlite|sqlite3|dump|pem|key)$')
        # Sanity: expected content is present.
        self.assertTrue(any(n.endswith('app/__init__.py') for n in names))
        self.assertTrue(any(n.endswith('.env.example') for n in names))


if __name__ == '__main__':
    unittest.main()
