"""Release audit checks for the bundled curriculum."""

import unittest
from unittest.mock import patch

from scripts.audit_curriculum import (
    _plain_language_gaps,
    _validate_plain_language_coverage,
    _validate_placement,
    audit,
)
from app.curriculum import _lesson_concepts


def fixture_lesson():
    return {
        'id': '5.01',
        'module_id': '05',
        'title': 'Retrieval decides what the model sees',
        'subtitle': 'Split documents into retrievable chunks, embed them, and match a question to the closest passage.',
        'core_concepts': [
            {'title': 'Chunking', 'content': 'Splitting documents into retrievable units.'},
            {'title': 'Similarity search', 'content': 'Matching a question to stored vectors.'},
        ],
        'questions': ['What does chunking decide?', 'What does a bad match cause?'],
    }


def curated_entry(lesson):
    return {
        'intro': (
            'Retrieval picks the passages a model gets to read. Most wrong answers '
            'start here, with the right model holding the wrong text.'
        ),
        'concepts': [
            {
                'title': concept['title'],
                'plain': (
                    'A chunk is the slice of a document stored on its own. Slice too '
                    'big and the search returns noise; too small and the answer is split apart.'
                ),
                'example': "A 40-page policy cut into 12 sections of about 800 words each.",
            }
            for concept in _lesson_concepts(lesson)
        ],
        'answers': [
            'Chunking decides the smallest unit a search can return, so it bounds the answer.',
            'A bad match sends the model text that does not contain the fact it needs.',
        ],
    }


def scope_overrides():
    return {
        'course': {
            'plain_language_scope': {'modules': ['05'], 'lesson_ids': []},
        },
    }


def placement_fixture():
    questions = []
    for index in range(1, 11):
        if index % 3 == 0:
            questions.append({
                'id': f'q{index}',
                'topic': 'setup_runtime',
                'type': 'short',
                'prompt': f'Short question {index}?',
                'answer': 'eight',
                'accepted_answers': ['eight', 'line 8'],
            })
        else:
            questions.append({
                'id': f'q{index}',
                'topic': 'setup_runtime',
                'prompt': f'Question {index}?',
                'options': ['first', 'second'],
                'answer': 1,
            })
    return {
        'passing_score': 8,
        'skippable_lessons': ['0.06', '0.07', '1.01'],
        'topics': [
            {'id': 'setup_runtime', 'title': 'Setup and running code',
             'questions': [q['id'] for q in questions], 'lessons': ['0.06', '0.07', '1.01']},
        ],
        'questions': questions,
    }


class CurriculumAuditTests(unittest.TestCase):
    def test_bundled_curriculum_passes_hard_release_checks(self):
        errors, modules, lessons, exercises, queue, gaps = audit(
            strict_reviews=False, run_exercises=False,
        )
        self.assertEqual(errors, [])
        self.assertEqual(modules, 13)
        self.assertEqual(lessons, 213)
        self.assertGreaterEqual(exercises, 61)
        # Review queue and coverage gaps are reported, not hard failures
        # unless the lesson is inside the enforced plain-language scope.
        self.assertIsInstance(queue, list)
        self.assertIsInstance(gaps, list)

    def test_bundled_curriculum_covers_every_scoped_lesson(self):
        errors, _, _, _, _, gaps = audit(strict_reviews=False, run_exercises=False)
        self.assertEqual([error for error in errors if 'plain-language' in error], [])
        self.assertLessEqual(len(gaps), 140)


class PlainLanguageCoverageTests(unittest.TestCase):
    def setUp(self):
        # MODERN_TOPIC_IDS is additive scope the module fixtures do not carry.
        patcher = patch('scripts.audit_curriculum.MODERN_TOPIC_IDS', ())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.lesson = fixture_lesson()
        self.entry = curated_entry(self.lesson)

    def validate(self, lesson, entry):
        errors = []
        _validate_plain_language_coverage(
            errors, [lesson], scope_overrides(), {lesson['id']: entry}
        )
        return errors

    def test_curated_entry_is_accepted(self):
        self.assertEqual(self.validate(self.lesson, self.entry), [])

    def test_missing_entry_blocks_the_release(self):
        errors = []
        _validate_plain_language_coverage(errors, [self.lesson], scope_overrides(), {})
        self.assertIn('Lesson 5.01 has no curated plain-language explanation', errors)

    def test_placeholder_intro_is_blocked(self):
        self.entry['intro'] = (
            'Slow down, name the idea, and connect it to one concrete action before '
            'you move on to the next lesson in this module.'
        )
        self.assertTrue(any('placeholder text' in error for error in self.validate(self.lesson, self.entry)))

    def test_intro_repeating_the_subtitle_is_blocked(self):
        self.entry['intro'] = self.lesson['subtitle']
        self.assertTrue(
            any('repeats the subtitle' in error for error in self.validate(self.lesson, self.entry))
        )

    def test_short_concept_list_is_blocked(self):
        self.entry['concepts'] = self.entry['concepts'][:1]
        errors = self.validate(self.lesson, self.entry)
        self.assertTrue(any('explains 1 concepts but the page renders 2' in error for error in errors))

    def test_concept_without_a_worked_example_is_blocked(self):
        self.entry['concepts'][1]['example'] = self.entry['concepts'][1]['plain']
        errors = self.validate(self.lesson, self.entry)
        self.assertTrue(any('repeats its explanation as its example' in error for error in errors))
        self.entry['concepts'][1]['example'] = ''
        errors = self.validate(self.lesson, self.entry)
        self.assertTrue(any('concept 2 has no worked example' in error for error in errors))

    def test_answer_count_must_match_the_questions(self):
        self.entry['answers'] = self.entry['answers'][:1]
        self.assertTrue(
            any('needs 2 checkpoint answers' in error for error in self.validate(self.lesson, self.entry))
        )

    def test_gaps_are_reported_without_blocking(self):
        outside = dict(fixture_lesson(), id='7.02', module_id='07')
        self.assertEqual(_plain_language_gaps([outside], scope_overrides(), {}), ['7.02'])


class PlacementTopicTests(unittest.TestCase):
    def test_valid_topics_pass(self):
        errors = []
        _validate_placement(errors, {'placement': placement_fixture()}, {'0.06', '0.07', '1.01'})
        self.assertEqual(errors, [])

    def test_uncovered_skippable_lesson_is_blocked(self):
        placement = placement_fixture()
        placement['topics'][0]['lessons'] = ['0.06', '0.07']
        errors = []
        _validate_placement(errors, {'placement': placement}, {'0.06', '0.07', '1.01'})
        self.assertTrue(any('do not cover every skippable lesson' in error for error in errors))

    def test_question_without_a_topic_is_blocked(self):
        placement = placement_fixture()
        placement['topics'][0]['questions'] = placement['topics'][0]['questions'][:-1]
        errors = []
        _validate_placement(errors, {'placement': placement}, {'0.06', '0.07', '1.01'})
        self.assertTrue(any('belongs to no topic' in error for error in errors))

    def test_topic_lessons_stay_inside_the_foundation_ramp(self):
        placement = placement_fixture()
        placement['topics'][0]['lessons'].append('5.01')
        errors = []
        _validate_placement(errors, {'placement': placement}, {'0.06', '0.07', '1.01', '5.01'})
        self.assertTrue(any('outside skippable_lessons' in error for error in errors))

    def test_bundled_placement_ships_topics(self):
        errors, *_ = audit(strict_reviews=False, run_exercises=False)
        self.assertEqual([error for error in errors if 'Placement' in error], [])
