"""Deterministic pathway-fit assessment shown during first-run onboarding.

Why a weighted questionnaire rather than a knowledge test or an AI-generated
one:

- New learners are a valid onboarding cohort (``skill_level: 'new'``), so a
  knowledge test would measure schooling rather than fit, and readiness is
  already gated structurally: the Machine Learning pathway opens only after
  the shared Module 01 and 02 projects.
- An LLM-generated assessment would add an external dependency, rate limits,
  and nondeterminism at the single most important first-run moment. A weighted
  scoring function is unit-testable and works offline, matching the existing
  ``recommend_track`` pattern.
- The scenarios ask about goals and working preferences, which is what
  actually separates the two pathways: shipping AI-powered product features
  versus building and evaluating models from data.

Like the pace recommendation, the assessment **proposes** and never writes
silently: the proposal is stored as ``CoursePlan.pathway_proposal`` and the
learner's explicit confirmation becomes ``CoursePlan.pathway_destination``.
A near-tie proposes ``undecided`` so a weak signal never forces a choice.
"""

PATHWAY_DESTINATIONS = {
    'ai': 'AI Engineering course',
    'ml': 'Machine Learning Engineering pathway',
    'undecided': 'Either pathway (undecided)',
}

# A proposal needs a lead of at least this many points. Each question
# contributes at most 2 points to one side (a "both" option contributes 1 to
# each), so a 3-point lead means at least two clear preferences and never a
# single soft lean.
PROPOSAL_MIN_LEAD = 3


PATHWAY_FIT_QUESTIONS = [
    {
        'id': 'fit.outcome',
        'prompt': 'Six months from now, what would you rather show someone?',
        'options': [
            {
                'id': 'product-feature',
                'label': 'An AI feature inside a product people use',
                'description': 'Chat, search, or agents wired into a real application.',
                'weights': {'ai': 2, 'ml': 0},
            },
            {
                'id': 'trained-model',
                'label': 'A model I trained and the results it achieved',
                'description': 'Experiments on a dataset with metrics to back them up.',
                'weights': {'ai': 0, 'ml': 2},
            },
            {
                'id': 'both',
                'label': 'Both equally',
                'description': 'I am just as happy building the feature as the model.',
                'weights': {'ai': 1, 'ml': 1},
            },
        ],
    },
    {
        'id': 'fit.weekend',
        'prompt': 'Which task would you pick for a free weekend?',
        'options': [
            {
                'id': 'model-feature',
                'label': 'Build a chat or search feature that calls a language model',
                'description': 'Shape the prompt, handle the responses, polish the flow.',
                'weights': {'ai': 2, 'ml': 0},
            },
            {
                'id': 'train-evaluate',
                'label': 'Train a model on a dataset and compare its accuracy',
                'description': 'Try features, tune settings, and beat your own baseline.',
                'weights': {'ai': 0, 'ml': 2},
            },
            {
                'id': 'either',
                'label': 'Either — I follow the interesting problem',
                'description': 'The tool matters less to me than the question.',
                'weights': {'ai': 1, 'ml': 1},
            },
        ],
    },
    {
        'id': 'fit.curiosity',
        'prompt': 'When an app does something clever with AI, what do you wonder first?',
        'options': [
            {
                'id': 'how-built',
                'label': 'How they built the experience and wired it together',
                'description': 'The product side: interfaces, integration, and behaviour.',
                'weights': {'ai': 2, 'ml': 0},
            },
            {
                'id': 'how-knows',
                'label': 'How the model knows what it knows, and when it fails',
                'description': 'The model side: data, evaluation, and limits.',
                'weights': {'ai': 0, 'ml': 2},
            },
            {
                'id': 'both-wonder',
                'label': 'Both, honestly',
                'description': 'I am curious about the whole path from data to screen.',
                'weights': {'ai': 1, 'ml': 1},
            },
        ],
    },
    {
        'id': 'fit.pride',
        'prompt': 'Which outcome would you be proudest of?',
        'options': [
            {
                'id': 'ship-ai',
                'label': 'Shipping an AI-powered feature end to end',
                'description': 'From idea to something other people can actually use.',
                'weights': {'ai': 2, 'ml': 0},
            },
            {
                'id': 'data-insight',
                'label': 'Finding a pattern in data that changed a decision',
                'description': 'Evidence from an evaluation that moved the needle.',
                'weights': {'ai': 0, 'ml': 2},
            },
            {
                'id': 'useful-either',
                'label': 'Finishing something useful either way',
                'description': 'Completion and craft matter more to me than the domain.',
                'weights': {'ai': 1, 'ml': 1},
            },
        ],
    },
    {
        'id': 'fit.workday',
        'prompt': 'Picture your ideal working day. It is mostly…',
        'options': [
            {
                'id': 'design-ai',
                'label': 'Designing how AI fits into a product and its users’ hands',
                'description': 'Deciding what the feature should do and how it should feel.',
                'weights': {'ai': 2, 'ml': 0},
            },
            {
                'id': 'experiments',
                'label': 'Experiments: data, features, metrics, small improvements',
                'description': 'A loop of measuring, adjusting, and measuring again.',
                'weights': {'ai': 0, 'ml': 2},
            },
            {
                'id': 'mixed-day',
                'label': 'A mix of building and investigating',
                'description': 'Switching between shipping and digging into results.',
                'weights': {'ai': 1, 'ml': 1},
            },
        ],
    },
]


class PathwayFitError(ValueError):
    """Raised when submitted answers cannot be scored."""


def pathway_fit_question(question_id):
    """Return one assessment question by ID or ``None``."""
    return next(
        (question for question in PATHWAY_FIT_QUESTIONS
         if question['id'] == question_id),
        None,
    )


def validate_pathway_fit_answers(answers):
    """Return a dict of question ID to error message for missing/bad answers.

    An empty dict means every question was answered with one of its own
    valid option IDs.
    """
    errors = {}
    if not isinstance(answers, dict):
        answers = {}
    for question in PATHWAY_FIT_QUESTIONS:
        option_ids = {option['id'] for option in question['options']}
        if answers.get(question['id']) not in option_ids:
            errors[question['id']] = 'Choose one of the options.'
    return errors


def score_pathway_fit(answers):
    """Score assessment answers into a pathway proposal.

    Returns ``{'proposal', 'ai_score', 'ml_score', 'lead'}`` where proposal is
    one of ``ai``, ``ml``, or ``undecided``. Raises :class:`PathwayFitError`
    when any answer is missing or unknown — callers should validate first so
    the learner sees per-question messages instead.
    """
    errors = validate_pathway_fit_answers(answers)
    if errors:
        raise PathwayFitError('The pathway fit check has unanswered questions.')

    scores = {'ai': 0, 'ml': 0}
    for question in PATHWAY_FIT_QUESTIONS:
        chosen = next(
            option for option in question['options']
            if option['id'] == answers[question['id']]
        )
        for side, weight in chosen['weights'].items():
            scores[side] += weight

    lead = scores['ai'] - scores['ml']
    if lead >= PROPOSAL_MIN_LEAD:
        proposal = 'ai'
    elif lead <= -PROPOSAL_MIN_LEAD:
        proposal = 'ml'
    else:
        proposal = 'undecided'
    return {
        'proposal': proposal,
        'ai_score': scores['ai'],
        'ml_score': scores['ml'],
        'lead': abs(lead),
    }
