import os
import tempfile
import unittest
from io import BytesIO
from urllib.parse import urlsplit

from app import create_app, db
from app.models import User, UserProfilePhoto


class ProfilePhotoTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        response = self.client.post('/register', data={
            'username': 'photo-learner',
            'email': 'photo-learner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Photo Learner',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def test_photo_upload_is_durable_and_displayed_in_profile(self):
        image = b'\x89PNG\r\n\x1a\nprofile-image-bytes'
        response = self.client.post(
            '/account/update',
            data={'profile_photo_file': (BytesIO(image), 'portrait.png')},
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('profile-photo/', response.get_data(as_text=True))

        with self.app.app_context():
            user = User.query.filter_by(username='photo-learner').one()
            photo_url = user.profile_photo
            stored = UserProfilePhoto.query.filter_by(user_id=user.id).one()
            self.assertEqual(stored.data, image)
            self.assertEqual(stored.mime_type, 'image/png')

        photo_response = self.client.get(urlsplit(photo_url).path)
        self.assertEqual(photo_response.status_code, 200)
        self.assertEqual(photo_response.mimetype, 'image/png')
        self.assertEqual(photo_response.data, image)

    def test_photo_can_be_removed_and_invalid_image_content_is_rejected(self):
        invalid = self.client.post(
            '/account/update',
            data={'profile_photo_file': (BytesIO(b'not a PNG'), 'portrait.png')},
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        self.assertIn('Choose a valid PNG', invalid.get_data(as_text=True))

        image = b'\xff\xd8\xffphoto-image-bytes'
        self.client.post(
            '/account/update',
            data={'profile_photo_file': (BytesIO(image), 'portrait.jpg')},
            content_type='multipart/form-data',
        )
        removed = self.client.post(
            '/account/update', data={'remove_profile_photo': 'true'}
        )
        self.assertEqual(removed.status_code, 302)
        with self.app.app_context():
            user = User.query.filter_by(username='photo-learner').one()
            self.assertIsNone(user.profile_photo)
            self.assertIsNone(
                UserProfilePhoto.query.filter_by(user_id=user.id).first()
            )


if __name__ == '__main__':
    unittest.main()
