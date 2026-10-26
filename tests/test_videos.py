import unittest

from app.videos import (
    build_lesson_video,
    format_duration,
    parse_timestamp,
    parse_video_id,
)


class VideoMetadataTests(unittest.TestCase):
    def test_parse_video_id_supports_common_youtube_urls(self):
        expected = 'K5KVEU3aaeQ'
        for url in (
            'https://www.youtube.com/watch?v=K5KVEU3aaeQ',
            'https://youtube.com/watch?v=K5KVEU3aaeQ&t=30s',
            'https://m.youtube.com/watch?v=K5KVEU3aaeQ',
            'https://youtu.be/K5KVEU3aaeQ?t=30',
            'https://www.youtube.com/embed/K5KVEU3aaeQ?start=30',
            'https://www.youtube.com/shorts/K5KVEU3aaeQ',
            'https://www.youtube-nocookie.com/embed/K5KVEU3aaeQ',
        ):
            with self.subTest(url=url):
                self.assertEqual(parse_video_id(url), expected)

    def test_parse_video_id_rejects_non_youtube_or_malformed_urls(self):
        for url in (
            None,
            '',
            'https://example.com/watch?v=K5KVEU3aaeQ',
            'https://www.youtube.com/watch?v=short',
            'https://www.youtube.com/',
            'not a url',
        ):
            with self.subTest(url=url):
                self.assertIsNone(parse_video_id(url))

    def test_timestamps_accept_integers_and_clock_strings(self):
        self.assertEqual(parse_timestamp(90), 90)
        self.assertEqual(parse_timestamp('90'), 90)
        self.assertEqual(parse_timestamp('1:30'), 90)
        self.assertEqual(parse_timestamp('1:02:03'), 3723)
        self.assertIsNone(parse_timestamp('abc'))
        self.assertIsNone(parse_timestamp(-1))
        self.assertIsNone(parse_timestamp(True))

    def test_build_lesson_video_normalizes_embed_and_clip_length(self):
        video = build_lesson_video({
            'title': 'A lesson video',
            'url': 'https://youtu.be/ZDa-Z5JzLYM',
            'channel': 'Example Channel',
            'start': '1:00',
            'end': 180,
            'why': 'A practical walkthrough.',
        })
        self.assertEqual(video['id'], 'ZDa-Z5JzLYM')
        self.assertEqual(video['url'], 'https://www.youtube.com/watch?v=ZDa-Z5JzLYM')
        self.assertIn('youtube-nocookie.com/embed/ZDa-Z5JzLYM', video['embed_url'])
        self.assertEqual(video['start'], 60)
        self.assertEqual(video['end'], 180)
        self.assertEqual(video['duration_seconds'], 120)
        self.assertEqual(video['channel'], 'Example Channel')
        self.assertEqual(video['why'], 'A practical walkthrough.')

    def test_build_lesson_video_accepts_an_enriched_bare_video_id(self):
        video = build_lesson_video({
            'video_id': 'K5KVEU3aaeQ',
            'title': 'Enriched video',
            'channel': 'Example Channel',
            'duration_seconds': 600,
        })
        self.assertEqual(video['id'], 'K5KVEU3aaeQ')
        self.assertEqual(video['duration_seconds'], 600)

    def test_build_lesson_video_returns_none_without_a_valid_id(self):
        self.assertIsNone(build_lesson_video(None))
        self.assertIsNone(build_lesson_video({}))
        self.assertIsNone(build_lesson_video({'url': 'https://example.com'}))

    def test_format_duration(self):
        self.assertEqual(format_duration(65), '1:05')
        self.assertEqual(format_duration(3723), '1:02:03')
        self.assertEqual(format_duration(None), '')
        self.assertEqual(format_duration(-1), '')
