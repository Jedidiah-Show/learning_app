"""Content integrity checks for the shipped curriculum files.

These tests institutionalize the manual audit: any release that breaks the
shape of the DynamoAI curriculum, the lesson extras, either specialization
pathway, the practice exercises, or the arena problems fails the suite.
"""

import ast
import json
import re
import unittest
from pathlib import Path

DATA = Path(__file__).parents[1] / 'app' / 'data'
PLACEHOLDER = re.compile(
    r'\b(TODO|TBD|FIXME|XXX|lorem ipsum|placeholder text|coming soon)\b', re.I
)


def _load(name):
    with (DATA / name).open(encoding='utf-8') as source:
        return json.load(source)


class DynamoCurriculumIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curriculum = _load('dynamoai_curriculum.json')
        cls.lessons = cls.curriculum['lessons']
        cls.extras = _load('lesson_extras.json')

    def test_lesson_ids_are_unique_and_match_module_prefix(self):
        ids = [lesson['id'] for lesson in self.lessons]
        self.assertEqual(len(ids), len(set(ids)))
        modules = {module['id']: int(module['id']) for module in self.curriculum['modules']}
        for lesson in self.lessons:
            self.assertEqual(
                int(lesson['id'].split('.')[0]), modules[lesson['module_id']],
                f"lesson {lesson['id']} id does not match its module",
            )

    def test_module_lesson_counts_match_the_lessons_list(self):
        counts = {lesson['module_id'] for lesson in self.lessons}
        for module in self.curriculum['modules']:
            module_lessons = [l for l in self.lessons if l['module_id'] == module['id']]
            self.assertEqual(len(module_lessons), module['lesson_count'])
            self.assertEqual(len(module['lessons']), module['lesson_count'])
            for position, lesson in enumerate(module_lessons, start=1):
                meta = lesson.get('meta', '')
                match = re.search(r'Lesson (\d+) of (\d+)', meta)
                self.assertIsNotNone(match, f"lesson {lesson['id']} meta lacks numbering")
                self.assertEqual(int(match.group(1)), position)
                self.assertEqual(int(match.group(2)), len(module_lessons))

    def test_lessons_have_the_core_blocks(self):
        for lesson in self.lessons:
            for key in ('why_it_matters', 'outcomes', 'core_concepts',
                        'steps', 'questions', 'tasks'):
                self.assertTrue(lesson.get(key), f"lesson {lesson['id']} missing {key}")
            for concept in lesson['core_concepts']:
                self.assertTrue(concept.get('title'))
                self.assertTrue(concept.get('content'))
                self.assertIsNone(PLACEHOLDER.search(concept['content']),
                                  f"lesson {lesson['id']} concept placeholder")

    def test_extras_are_consistent_with_questions(self):
        # Mirrors the audit scope rule: enforced lessons carry full curated
        # extras (answers aligned with the questions, examples on every
        # concept). Outside the scope a lesson may ship an intro-only entry,
        # and the lesson page renders the self-check without answer keys.
        from scripts.audit_curriculum import _plain_language_scope
        overrides = _load('curriculum_overrides.json')
        scope = _plain_language_scope(overrides, self.lessons)
        question_counts = {l['id']: len(l.get('questions', [])) for l in self.lessons}
        for lesson_id, extra in self.extras.items():
            self.assertIn(lesson_id, question_counts)
            self.assertTrue(extra.get('intro', '').strip())
            if lesson_id not in scope:
                continue
            answers = extra.get('answers')
            self.assertIsNotNone(answers)
            self.assertEqual(
                len(answers), question_counts[lesson_id],
                f'extras for {lesson_id} carry {len(answers)} answers '
                f'for {question_counts[lesson_id]} questions',
            )
            for concept in extra.get('concepts', []):
                self.assertTrue(concept.get('plain', '').strip(),
                                f'extras {lesson_id} concept missing plain explanation')
                self.assertTrue(concept.get('example', '').strip(),
                                f'extras {lesson_id} concept missing worked example')


def _pathway_lessons(name):
    pathway = _load(name)
    modules = pathway['modules']
    lessons = [lesson for module in modules for lesson in module['lessons']]
    return pathway, modules, lessons


class PathwayIntegrityTests(unittest.TestCase):
    def _check_pathway(self, name, require_task):
        pathway, modules, lessons = _pathway_lessons(name)
        ids = [lesson['id'] for lesson in lessons]
        self.assertEqual(len(ids), len(set(ids)), f'{name} has duplicate lesson ids')
        self.assertGreaterEqual(len(modules), 1)
        for lesson in lessons:
            self.assertEqual(lesson.get('status'), 'ready')
            self.assertTrue(lesson.get('goal', '').strip(),
                            f"{lesson['id']} missing goal")
            self.assertGreater(lesson.get('study_minutes', 0), 0,
                               f"{lesson['id']} invalid study_minutes")
            sections = lesson.get('sections', [])
            self.assertTrue(sections, f"{lesson['id']} has no sections")
            for section in sections:
                self.assertTrue(section.get('heading'),
                                f"{lesson['id']} section missing heading")
                self.assertTrue(any(str(p).strip() for p in section.get('body', [])),
                                 f"{lesson['id']} section {section.get('heading')!r} empty")
                for paragraph in section['body']:
                    self.assertIsNone(PLACEHOLDER.search(str(paragraph)),
                                      f'{lesson["id"]} placeholder in section')
            quiz = lesson.get('quiz') or {}
            choices = quiz.get('choices', [])
            self.assertGreaterEqual(len(choices), 2, f"{lesson['id']} quiz too short")
            self.assertEqual(len(set(choices)), len(choices),
                             f"{lesson['id']} duplicate quiz choices")
            self.assertIsInstance(quiz.get('answer'), int)
            self.assertGreaterEqual(quiz['answer'], 0)
            self.assertLess(quiz['answer'], len(choices))
            self.assertTrue(quiz.get('explanation', '').strip(),
                            f"{lesson['id']} quiz missing explanation")
            if require_task:
                self.assertTrue(lesson.get('task', '').strip(),
                                f"{lesson['id']} missing hands-on task")

    def test_machine_learning_pathway(self):
        self._check_pathway('machine_learning_pathway.json', require_task=True)

    def test_cloud_ai_infrastructure_pathway(self):
        self._check_pathway('cloud_ai_infrastructure_pathway.json', require_task=True)


class PracticeExerciseIntegrityTests(unittest.TestCase):
    def test_exercises_are_valid_and_reference_real_lessons(self):
        lessons = _load('dynamoai_curriculum.json')['lessons']
        lesson_ids = {lesson['id'] for lesson in lessons}
        exercises = _load('practice_exercises.json')
        self.assertGreaterEqual(len(exercises), 62)
        seen = set()
        for exercise in exercises:
            self.assertNotIn(exercise['id'], seen)
            seen.add(exercise['id'])
            self.assertIn(exercise['lesson_id'], lesson_ids)
            self.assertIn(exercise['difficulty'], {'beginner', 'intermediate', 'advanced'})
            self.assertTrue(exercise['skills'])
            self.assertIn('checks_code', exercise)
            compile(
                exercise['checks_code'], exercise['id'], 'exec',
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )

    def test_exercise_prerequisites_resolve(self):
        exercises = {e['id']: e for e in _load('practice_exercises.json')}
        for exercise in exercises.values():
            for prerequisite in exercise['prerequisites']:
                self.assertIn(prerequisite, exercises)
                self.assertNotEqual(prerequisite, exercise['id'])

    def test_every_exercise_solution_passes_its_checks(self):
        exercises = _load('practice_exercises.json')
        for exercise in exercises:
            namespace = {'__name__': '__main__'}
            source = (
                exercise['solution_code'] + '\n\n' + exercise['checks_code']
            )
            code = compile(
                source, exercise['id'], 'exec',
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )
            outcome = eval(code, namespace)
            import inspect
            import asyncio
            if inspect.isawaitable(outcome):
                asyncio.run(outcome)

    def test_every_exercise_has_a_private_judge_suite_that_passes(self):
        # The server-side judge falls back to the public browser checks when
        # judge_tests is absent; every exercise must instead ship a dedicated
        # hidden suite that the reference solution passes.
        import asyncio
        import inspect
        for exercise in _load('practice_exercises.json'):
            with self.subTest(exercise=exercise['id']):
                suite = exercise.get('judge_tests', '')
                self.assertTrue(suite.strip(), 'missing judge_tests')
                self.assertNotEqual(
                    suite.strip(), exercise['checks_code'].strip(),
                    'judge_tests must be a dedicated suite, not a copy of the public checks',
                )
                compile(
                    suite, exercise['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
                namespace = {'__name__': '__main__'}
                source = exercise['solution_code'] + '\n\n' + suite
                code = compile(
                    source, exercise['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
                outcome = eval(code, namespace)
                if inspect.isawaitable(outcome):
                    asyncio.run(outcome)


class PathwayPracticeExerciseIntegrityTests(unittest.TestCase):
    def test_pathway_exercises_reference_real_pathway_lessons(self):
        ml = _load('machine_learning_pathway.json')
        cai = _load('cloud_ai_infrastructure_pathway.json')
        pathway_lesson_ids = {
            lesson['id']
            for pathway in (ml, cai)
            for module in pathway['modules']
            for lesson in module['lessons']
        }
        exercises = _load('pathway_practice_exercises.json')
        self.assertGreaterEqual(len(exercises), 22)
        seen = set()
        for exercise in exercises:
            self.assertNotIn(exercise['id'], seen)
            seen.add(exercise['id'])
            self.assertIn(exercise['lesson_id'], pathway_lesson_ids)
            self.assertIn(exercise['difficulty'], {'beginner', 'intermediate', 'advanced'})
            self.assertTrue(exercise['skills'])
            compile(
                exercise['checks_code'], exercise['id'], 'exec',
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )

    def test_pathway_exercise_solutions_pass_their_checks(self):
        import asyncio
        import inspect

        for exercise in _load('pathway_practice_exercises.json'):
            source = exercise['solution_code'] + '\n\n' + exercise['checks_code']
            namespace = {'__name__': '__main__'}
            code = compile(
                source, exercise['id'], 'exec',
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )
            outcome = eval(code, namespace)
            if inspect.isawaitable(outcome):
                asyncio.run(outcome)


if __name__ == '__main__':
    unittest.main()
