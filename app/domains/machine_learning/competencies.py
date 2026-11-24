"""Machine Learning competencies domain catalog.

Defines the core competencies, lesson mappings, and project mappings
specific to the Machine Learning specialization pathway.
"""

from __future__ import annotations

ML_COMPETENCIES = {
    'ml-mathematics-statistics': {
        'title': 'Mathematics and statistics',
        'category': 'Machine Learning',
    },
    'ml-python-programming': {
        'title': 'Python programming',
        'category': 'Machine Learning',
    },
    'ml-data-analysis': {
        'title': 'Data analysis',
        'category': 'Machine Learning',
    },
    'ml-data-preparation': {
        'title': 'Data preparation',
        'category': 'Machine Learning',
    },
    'ml-feature-engineering': {
        'title': 'Feature engineering',
        'category': 'Machine Learning',
    },
    'ml-supervised-learning': {
        'title': 'Supervised learning',
        'category': 'Machine Learning',
    },
    'ml-unsupervised-learning': {
        'title': 'Unsupervised learning',
        'category': 'Machine Learning',
    },
    'ml-model-evaluation': {
        'title': 'Model evaluation',
        'category': 'Machine Learning',
    },
    'ml-deep-learning': {
        'title': 'Deep learning',
        'category': 'Machine Learning',
    },
    'ml-deployment': {
        'title': 'ML deployment',
        'category': 'Machine Learning',
    },
    'ml-mlops': {
        'title': 'MLOps',
        'category': 'Machine Learning',
    },
    'ml-responsible-ml': {
        'title': 'Responsible ML',
        'category': 'Machine Learning',
    },
}

ML_LESSON_COMPETENCIES = {
    'mle.tools.01': {'ml-responsible-ml'},
    'mle.tools.02': {'ml-python-programming', 'ml-responsible-ml'},
    'mle.tools.03': {'ml-python-programming'},
    'mle.tools.04': {'ml-python-programming', 'ml-responsible-ml'},
    'mle.math.00': {'ml-mathematics-statistics'},
    'mle.math.01': {'ml-mathematics-statistics'},
    'mle.math.02': {'ml-mathematics-statistics'},
    'mle.math.03': {'ml-mathematics-statistics'},
    'mle.math.04': {'ml-mathematics-statistics'},
    'mle.math.05': {'ml-mathematics-statistics'},
    'mle.math.06': {'ml-mathematics-statistics'},
    'mle.math.07': {'ml-mathematics-statistics'},
    'mle.math.08': {'ml-mathematics-statistics'},
    'mle.data.01': {'ml-data-analysis', 'ml-model-evaluation', 'ml-responsible-ml'},
    'mle.data.02': {'ml-data-analysis', 'ml-data-preparation'},
    'mle.data.03': {'ml-data-preparation', 'ml-model-evaluation'},
    'mle.data.04': {
        'ml-data-preparation', 'ml-feature-engineering', 'ml-responsible-ml',
    },
    'mle.classical.01': {'ml-supervised-learning', 'ml-model-evaluation'},
    'mle.classical.02': {'ml-data-preparation', 'ml-supervised-learning'},
    'mle.classical.03': {'ml-model-evaluation'},
    'mle.classical.04': {'ml-model-evaluation'},
    'mle.data.05': {'ml-data-analysis', 'ml-data-preparation'},
    'mle.data.06': {'ml-data-preparation', 'ml-responsible-ml'},
    'mle.data.07': {'ml-data-preparation', 'ml-feature-engineering'},
    'mle.data.08': {'ml-feature-engineering'},
    'mle.classical.05': {'ml-supervised-learning'},
    'mle.classical.06': {'ml-supervised-learning'},
    'mle.classical.07': {'ml-model-evaluation'},
    'mle.classification.01': {'ml-supervised-learning', 'ml-model-evaluation'},
    'mle.classification.02': {'ml-supervised-learning'},
    'mle.classification.03': {'ml-supervised-learning'},
    'mle.classification.04': {'ml-supervised-learning'},
    'mle.classification.05': {'ml-model-evaluation'},
    'mle.unsupervised.01': {'ml-unsupervised-learning'},
    'mle.unsupervised.02': {'ml-unsupervised-learning'},
    'mle.unsupervised.03': {'ml-unsupervised-learning', 'ml-model-evaluation'},
    'mle.unsupervised.04': {'ml-unsupervised-learning'},
    'mle.unsupervised.05': {'ml-unsupervised-learning', 'ml-feature-engineering'},
    'mle.deeplearning.01': {'ml-deep-learning'},
    'mle.deeplearning.02': {'ml-deep-learning'},
    'mle.deeplearning.03': {'ml-deep-learning'},
    'mle.deeplearning.04': {'ml-deep-learning', 'ml-model-evaluation'},
    'mle.deeplearning.05': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.vision.01': {'ml-deep-learning'},
    'mle.vision.02': {'ml-data-preparation', 'ml-deep-learning'},
    'mle.vision.03': {'ml-deep-learning'},
    'mle.vision.04': {'ml-deep-learning'},
    'mle.vision.05': {'ml-deep-learning', 'ml-model-evaluation'},
    'mle.vision.06': {'ml-model-evaluation', 'ml-responsible-ml'},
    'mle.repro.01': {'ml-mlops'},
    'mle.repro.02': {'ml-mlops'},
    'mle.repro.03': {'ml-mlops', 'ml-model-evaluation'},
    'mle.production.01': {'ml-deployment'},
    'mle.production.02': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
    'mle.production.03': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
    'mle.pytorch.01': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.pytorch.02': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.capstone.01': {
        'ml-python-programming', 'ml-data-analysis', 'ml-data-preparation',
        'ml-feature-engineering', 'ml-supervised-learning',
        'ml-model-evaluation', 'ml-deep-learning', 'ml-deployment', 'ml-mlops',
        'ml-responsible-ml',
    },
    'mle.capstone.02': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
}

ML_PROJECT_COMPETENCIES = {
    'mle.ai-tools': {
        'ml-python-programming', 'ml-responsible-ml',
    },
    'mle.math-foundations': {'ml-mathematics-statistics', 'ml-data-analysis'},
    'mle.classification-models': {
        'ml-supervised-learning', 'ml-model-evaluation',
    },
    'mle.unsupervised-learning': {
        'ml-unsupervised-learning', 'ml-model-evaluation',
    },
    'mle.deep-learning': {'ml-deep-learning', 'ml-model-evaluation'},
    'mle.computer-vision': {'ml-deep-learning', 'ml-model-evaluation'},
    'mle.data-problem-formulation': {
        'ml-python-programming', 'ml-data-analysis', 'ml-data-preparation',
        'ml-feature-engineering', 'ml-responsible-ml',
    },
    'mle.classical-ml': {
        'ml-data-preparation', 'ml-supervised-learning', 'ml-model-evaluation',
    },
    'mle.reproducible-training': {'ml-mlops', 'ml-model-evaluation'},
    'mle.production-ml': {'ml-deployment', 'ml-mlops', 'ml-responsible-ml'},
    'mle.pytorch-advanced': {'ml-deep-learning', 'ml-supervised-learning'},
    'mle.capstone-integration': {
        'ml-python-programming', 'ml-data-analysis', 'ml-data-preparation',
        'ml-feature-engineering', 'ml-supervised-learning',
        'ml-model-evaluation', 'ml-deep-learning', 'ml-deployment', 'ml-mlops',
        'ml-responsible-ml',
    },
}
