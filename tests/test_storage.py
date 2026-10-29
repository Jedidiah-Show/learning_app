import os
import tempfile
import unittest

from app import create_app
from app.storage import LocalStorage, StorageError, get_storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            STORAGE_BACKEND='local',
            UPLOAD_FOLDER=os.path.join(self.temp_dir.name, 'uploads'),
        )

    def tearDown(self):
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def test_local_storage_saves_reads_and_deletes_files(self):
        with self.app.app_context():
            storage = get_storage()
            self.assertIsInstance(storage, LocalStorage)
            storage.save('course/file.txt', b'hello', 'text/plain')
            self.assertTrue(storage.exists('course/file.txt'))
            self.assertEqual(
                storage.read('course/file.txt'), (b'hello', 'text/plain')
            )
            storage.delete('course/file.txt')
            self.assertFalse(storage.exists('course/file.txt'))

    def test_local_storage_rejects_path_traversal(self):
        with self.app.app_context():
            storage = get_storage()
            with self.assertRaises(StorageError):
                storage.save('../outside.txt', b'nope')
            with self.assertRaises(StorageError):
                storage.read('/etc/passwd')


if __name__ == '__main__':
    unittest.main()
