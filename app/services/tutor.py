"""AI Tutor 2.0 - Context-aware instructional guidance engine.

Provides Socratic hinting, knowledge gap diagnosis, and context-aware
responses spanning execution errors, recent submissions, and skill passport
state. Features a 5-stage progressive hinting engine for practice troubleshooting.

Supports domain-aware tutoring: AI Engineering and Machine Learning learners
receive domain-appropriate hints and guidance based on their active pathway
enrolment.
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from app.models import TutorConversation
from app.pathway_scope import destination_for


# ────────────────────────────────────────────────────────────────────────────
# Stage 1: Concept Hint
# ────────────────────────────────────────────────────────────────────────────
CONCEPT_HINT_TEMPLATE = (
    "💡 *Concept hint:* Focus on the core concept you need to apply here. "
    "What is the main problem you're trying to solve?"
)


# ────────────────────────────────────────────────────────────────────────────
# Stage 2: Approach Hint
# ────────────────────────────────────────────────────────────────────────────
APPROACH_HINT_TEMPLATE = (
    "🧭 *Approach hint:* Consider breaking the problem into smaller steps. "
    "What would be your first step toward a solution?"
)


# ────────────────────────────────────────────────────────────────────────────
# Stage 3: Edge Case Hint
# ────────────────────────────────────────────────────────────────────────────
EDGE_CASE_HINT_TEMPLATE = (
    "⚠️ *Edge case hint:* Think about boundary conditions and special inputs. "
    "What happens when your input is empty, null, or at its extremes?"
)


# ────────────────────────────────────────────────────────────────────────────
# Stage 4: Pseudocode Hint
# ────────────────────────────────────────────────────────────────────────────
PSEUDOCODE_HINT_TEMPLATE = (
    "📝 *Pseudocode hint:* Here's the algorithm in plain language. Can you "
    "translate this into Python?"
)


# ────────────────────────────────────────────────────────────────────────────
# Stage 5: Editorial / Solution
# ────────────────────────────────────────────────────────────────────────────
EDITORIAL_HINT_TEMPLATE = (
    "📖 *Editorial:* The reference solution with walkthrough explanations. "
    "Use this to understand each decision in your own words."
)


# ────────────────────────────────────────────────────────────────────────────
# Hint Payloads
# ────────────────────────────────────────────────────────────────────────────
HINT_STAGES: Dict[int, str] = {
    1: CONCEPT_HINT_TEMPLATE,
    2: APPROACH_HINT_TEMPLATE,
    3: EDGE_CASE_HINT_TEMPLATE,
    4: PSEUDOCODE_HINT_TEMPLATE,
    5: EDITORIAL_HINT_TEMPLATE,
}


# ────────────────────────────────────────────────────────────────────────────
# Domain-aware tutoring helpers (M5.1-M5.5)
# ────────────────────────────────────────────────────────────────────────────

DOMAIN_SHARED_FOUNDATIONS = 'shared-foundations'
DOMAIN_AI_ENGINEERING = 'ai-engineering'
DOMAIN_MACHINE_LEARNING = 'machine-learning'

DOMAIN_PROFILES = {
    DOMAIN_SHARED_FOUNDATIONS: {
        'label': 'Shared Foundations',
        'greeting': (
            'Hello! I’m Ruach-AI, your Shared Foundations tutor. '
            'I can help you with Python, programming logic, software engineering, '
            'APIs, debugging, and development workflow.'
        ),
        'focus': (
            'Python explanations, programming logic, software engineering, APIs, '
            'debugging, and development workflow.'
        ),
        'socratic_prompts': [
            'What do you think this piece of code is responsible for?',
            'Which input or state changes first, and why?',
            'If this failed, what would you check before changing code?',
        ],
    },
    DOMAIN_AI_ENGINEERING: {
        'label': 'AI Engineering',
        'greeting': (
            'Hello! I’m Ruach-AI, your AI Engineering tutor. '
            'I can help you with LLM applications, prompting, retrieval, RAG, '
            'agents, tool integration, evaluation, and AI deployment.'
        ),
        'focus': (
            'LLM applications, prompt engineering, retrieval, RAG, agents, '
            'tool integration, evaluation, AI security, and deployment.'
        ),
        'socratic_prompts': [
            'What behavior do you want the model or agent to produce?',
            'What evidence would show this prompt or retrieval change helped?',
            'Where could this system fail silently in production?',
        ],
    },
    DOMAIN_MACHINE_LEARNING: {
        'label': 'Machine Learning Engineering',
        'greeting': (
            'Hello! I’m Ruach-AI, your Machine Learning tutor. '
            'I can help you with mathematics, statistics, data preparation, '
            'algorithms, evaluation, experimentation, deep learning, and MLOps.'
        ),
        'focus': (
            'Mathematics, statistics, data analysis/preparation, algorithms, '
            'model evaluation, experimentation, deep learning, and MLOps.'
        ),
        'socratic_prompts': [
            'What does the data tell you before you choose a model?',
            'How would you know if this result generalizes beyond this split?',
            'Which metric matches the real cost of a wrong prediction here?',
        ],
    },
}


def infer_learning_domain(
    lesson_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    destination: Optional[str] = None,
) -> str:
    """Return the explicit tutoring domain for the current context."""
    if lesson_id and str(lesson_id).startswith('mle.'):
        return DOMAIN_MACHINE_LEARNING
    if problem_id:
        try:
            from app.practice_arena import get_arena_problem
            problem = get_arena_problem(problem_id) or {}
        except Exception:
            problem = {}
        track = (problem.get('track') or '').strip().lower()
        if track == 'machine-learning':
            return DOMAIN_MACHINE_LEARNING
        if track == 'ai-engineering':
            return DOMAIN_AI_ENGINEERING
    if destination == 'machine-learning':
        return DOMAIN_MACHINE_LEARNING
    if destination == 'ai-engineering':
        return DOMAIN_AI_ENGINEERING
    # AI course modules 00-02 are the shared foundation in current course shape.
    if lesson_id:
        prefix = str(lesson_id).split('.', 1)[0]
        if prefix in {'00', '01', '02', 'sf'}:
            return DOMAIN_SHARED_FOUNDATIONS
        if prefix.isdigit():
            return DOMAIN_AI_ENGINEERING
    if destination in (None, 'shared-foundations', 'undecided'):
        return DOMAIN_SHARED_FOUNDATIONS
    return DOMAIN_SHARED_FOUNDATIONS


def _domain_profile(domain: str) -> Dict[str, Any]:
    return DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES[DOMAIN_SHARED_FOUNDATIONS])


def pathway_context_for_user(
    user_id: Optional[int] = None,
    *,
    lesson_id: Optional[str] = None,
    problem_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a domain-aware pathway/tutor context object (M5.1-M5.4)."""
    destination = destination_for(user_id) if user_id else None
    domain = infer_learning_domain(lesson_id, problem_id, destination)
    profile = _domain_profile(domain)
    context = {
        'active_domain': domain,
        'active_pathway': destination,
        'domain_label': profile['label'],
        'domain_focus': profile['focus'],
        'tutor_greeting': profile['greeting'],
        'socratic_prompts': list(profile.get('socratic_prompts') or []),
        # Legacy compatibility for older callers.
        'ai_focus': domain == DOMAIN_AI_ENGINEERING,
    }
    return context


def _ml_concept_hint(skills: str) -> str:
    """Return an ML-domain-specific concept hint when skills are ML-related."""
    skill_list = [s.strip().lower() for s in (skills or '').split(',') if s.strip()]
    if 'statistics' in skill_list or 'ml-statistics' in skill_list:
        return (
            " Remember that a statistic summarizes a sample: the mean is the "
            "balance point, the median is the middle value, and standard "
            "deviation measures spread around the mean."
        )
    if 'data-preparation' in skill_list or 'ml-data-analysis' in skill_list:
        return (
            " Data preparation is about making data safe and useful for "
            "modelling: handle missing values, scale features, and keep the "
            "train/validation/test boundary intact."
        )
    if any(skill in skill_list for skill in ('classification', 'regression', 'classical-ml')):
        return (
            " In supervised learning, you're learning a mapping from inputs "
            "to outputs. Start with a baseline, then measure how well it "
            "generalises to held-out data."
        )
    if 'deep-learning' in skill_list:
        return (
            " A neural network layer computes a weighted sum of inputs, adds "
            "a bias, then applies an activation. Each step is differentiable, "
            "which is what makes gradient-based training possible."
        )
    if 'model-evaluation' in skill_list:
        return (
            " Evaluation answers 'how good is the model?' using metrics "
            "chosen for the problem — accuracy alone can mislead on "
            "imbalanced data; precision, recall, and F1 tell a fuller story."
        )
    if 'ml-deployment' in skill_list or 'mlops' in skill_list:
        return (
            " Deployment means the model can be loaded and used outside the "
            "training notebook: serialise weights, preserve preprocessing, "
            "and validate inputs before predicting."
        )
    return ""


def _ai_concept_hint(skills: str) -> str:
    skill_list = [s.strip().lower() for s in (skills or '').split(',') if s.strip()]
    if 'prompt-engineering' in skill_list:
        return " Make the task, constraints, and expected format explicit so the model has less room to guess."
    if 'rag' in skill_list or 'retrieval' in skill_list:
        return " Retrieval quality and chunking shape the answer; inspect what evidence is actually returned."
    if 'agents' in skill_list or 'tool-use' in skill_list:
        return " Define tool contracts and stop conditions so the agent can act safely and know when it is done."
    if 'evaluation' in skill_list:
        return " Evaluate against representative cases and failure modes, not only the happy path."
    return ""


def _ml_edge_case_hint(skills: str) -> str:
    """Return an ML-domain-specific edge-case hint when skills are ML-related."""
    skill_list = [s.strip().lower() for s in (skills or '').split(',') if s.strip()]
    if 'statistics' in skill_list or 'ml-statistics' in skill_list:
        return " Watch for empty inputs (return None or a safe default) and zero standard deviation (division by zero when standardising)."
    if 'data-preparation' in skill_list or 'ml-data-analysis' in skill_list:
        return " Watch for missing values, mismatched list lengths, and ratios that do not sum to 1 when splitting data."
    if any(skill in skill_list for skill in ('classification', 'regression')):
        return " Watch for zero denominators in precision (TP + FP = 0) and recall (TP + FN = 0); guard them explicitly."
    if 'deep-learning' in skill_list:
        return " Watch for empty or mismatched input/weight lists — a neuron cannot compute without matching dimensions."
    if 'model-evaluation' in skill_list:
        return " Watch for empty or mismatched actual/predicted lists — metrics are undefined without aligned data."
    return ""


def _ml_pseudocode_hint(skills: str) -> str:
    """Return an ML-domain-specific pseudocode hint when skills are ML-related."""
    skill_list = [s.strip().lower() for s in (skills or '').split(',') if s.strip()]
    if 'statistics' in skill_list or 'ml-statistics' in skill_list:
        return " Guard empty input first. Accumulate totals/counts, then derive mean/median/variance from the validated sample."
    if 'data-preparation' in skill_list or 'ml-data-analysis' in skill_list:
        return " Validate inputs first, build a new structure rather than mutating unexpectedly, and preserve the intended order/split."
    if any(skill in skill_list for skill in ('classification', 'regression', 'model-evaluation')):
        return " Walk actual and predicted values in parallel, update confusion-matrix counts/errors, then derive the requested metric from those counts."
    if 'deep-learning' in skill_list:
        return " Validate dimensions, compute weighted sum + bias, then apply the activation before returning the output."
    return ""


def build_tutor_prompt_context(tutor_context: "TutorContext") -> Dict[str, Any]:
    """Minimal, domain-aware context payload for LLM prompts (M5.1)."""
    return {
        'pathway': tutor_context.pathway_context,
        'lesson': tutor_context.lesson_context,
        'exercise': {
            'problem_id': tutor_context.code.problem_id,
            'track': tutor_context.code.track,
            'skills': tutor_context.code.skills_involved,
        },
        'competency_evidence': {
            'demonstrated': tutor_context.passport.demonstrated_skills,
            'developing': tutor_context.passport.developing_skills,
            'not_started': tutor_context.passport.not_started_skills,
            'mastered': tutor_context.passport.mastered_skills,
        },
        'recent_submissions': tutor_context.recent_submissions[:3],
        'error_summary': tutor_context.error_summary,
    }


@dataclass
class CodeContext:
    """Context about the learner's code state for the AI Tutor."""

    code: str
    error_log: Optional[str] = None
    previous_attempts: int = 0
    time_spent_seconds: int = 0
    skills_involved: List[str] = field(default_factory=list)
    problem_id: Optional[str] = None
    track: Optional[str] = None
    hints: List[str] = field(default_factory=list)
    editorial: Optional[str] = None
    solution_code: Optional[str] = None


@dataclass
class PassportState:
    """Learner's Skill Passport state for tutor context."""

    demonstrated_skills: List[str] = field(default_factory=list)
    developing_skills: List[str] = field(default_factory=list)
    not_started_skills: List[str] = field(default_factory=list)
    mastered_skills: List[str] = field(default_factory=list)


@dataclass
class TutorContext:
    """Complete context package fed to the AI Tutor."""

    code: CodeContext
    passport: PassportState
    stage: int = 1  # Current hint stage (1-5)
    error_summary: Optional[str] = None
    socratic_guardrail: bool = True  # Prevent direct solution output
    recent_submissions: List[Dict[str, Any]] = field(default_factory=list)
    lesson_context: Dict[str, Any] = field(default_factory=dict)
    pathway_context: Dict[str, Any] = field(default_factory=dict)


class SocraticGuardrail:
    """Ensures tutor responses follow Socratic method - step-by-step guidance
    rather than providing direct solutions."""

    # Expanded list of solution-revealing patterns to catch
    PROHIBITED_PHRASES = [
        "the answer is",
        "here's the solution",
        "your code should be",
        "you should write",
        "the solution is",
        "solve it by",
        "your code must",
        "the correct answer",
    ]
    REPLACEMENTS = {
        "the answer is": "one approach to consider is...",
        "here's the solution": "one possible path forward is...",
        "your code should be": "one option is to...",
        "you should write": "you might consider writing...",
        "the solution is": "a possible solution path involves...",
        "solve it by": "one way to approach this is...",
        "your code must": "one option is to...",
        "the correct answer": "a correct result might be...",
    }

    @classmethod
    def validate_response(cls, response: str, *, allow_code: bool = False) -> str:
        """Validate and sanitize a tutor response through Socratic guardrails.

        Args:
            response: The raw AI response text.
            allow_code: If True, code blocks are preserved; otherwise replaced
                with guidance messages.

        Returns:
            Sanitized response that avoids prohibited solution-revealing phrases.

        Raises:
            ValueError: If the response cannot be sanitized without losing
                meaningful guidance.
        """
        import re

        # Remove code blocks if not allowed, replacing with guidance
        if not allow_code:
            response = re.sub(
                r"```[\s\S]*?```",
                "Try translating the idea into your own steps.",
                response,
            )

        original = response
        for phrase in cls.PROHIBITED_PHRASES:
            if phrase.lower() in response.lower():
                response = re.sub(
                    re.escape(phrase),
                    cls.REPLACEMENTS[phrase],
                    response,
                    flags=re.IGNORECASE,
                )

        # If no changes were made, check if the response is purely Socratic
        # (contains questions, guidance, no direct answers)
        if response == original:
            # Check if response contains any direct answer patterns
            answer_patterns = [r"^the answer is\s", r"^the solution is\s"]
            if re.search(r"answer is|solution is", response, re.IGNORECASE):
                raise ValueError(
                    "Response contains direct answer that cannot be sanitized"
                )

        return response


def assemble_tutor_context(
    user_id: int,
    lesson_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    code: Optional[str] = None,
    error_log: Optional[str] = None,
    recent_submissions: Optional[List[Dict]] = None,
    passport: Optional[Dict] = None,
) -> TutorContext:
    """Assemble complete tutor context from all available sources (M5.1).

    Includes domain/pathway, active lesson/module context, recent submissions,
    error state, exercise/project hints, and Skill Passport evidence so tutoring
    stays scoped to the learner's active domain.
    """
    from app.services.skill_passport import get_user_all_skill_states

    recent_submissions = recent_submissions or []
    if user_id and not recent_submissions:
        try:
            from app.models import Submission
            submissions_query = Submission.query.filter_by(user_id=user_id)
            if problem_id:
                submissions_query = submissions_query.filter_by(problem_id=problem_id)
            recent_submissions = [
                {
                    'problem_id': item.problem_id,
                    'verdict': item.verdict,
                    'error_details': item.error_details or '',
                    'submitted_at': item.submitted_at.isoformat() if item.submitted_at else None,
                }
                for item in submissions_query.order_by(
                    Submission.submitted_at.desc(),
                ).limit(5)
            ]
        except Exception:
            recent_submissions = []

    destination = destination_for(user_id) if user_id else None
    pathway_context = pathway_context_for_user(
        user_id, lesson_id=lesson_id, problem_id=problem_id
    )
    if destination is not None:
        pathway_context['active_pathway'] = destination

    problem = None
    if problem_id:
        try:
            from app.practice_arena import get_arena_problem
            problem = get_arena_problem(problem_id)
        except Exception:
            problem = None

    lesson_context = {}
    module_context = {}
    if lesson_id:
        lesson = None
        try:
            from app.curriculum import get_lesson
            lesson = get_lesson(lesson_id)
        except Exception:
            lesson = None
        if lesson is None:
            try:
                from app.ml_pathway import get_machine_learning_lesson
                lesson = get_machine_learning_lesson(lesson_id)
            except Exception:
                lesson = None
        if lesson:
            lesson_context = {
                key: lesson[key]
                for key in (
                    'id', 'title', 'outcomes', 'core_concepts', 'common_mistakes',
                    'why_it_matters', 'key_terms', 'checklist',
                )
                if lesson.get(key)
            }
            module = lesson.get('_module') or {}
            if not module and lesson.get('module_id'):
                module = {'id': lesson.get('module_id'), 'title': lesson.get('module_title')}
            module_context = {
                key: module[key]
                for key in ('id', 'number', 'title', 'description')
                if module.get(key) is not None
            }
    if module_context:
        pathway_context['current_module'] = module_context
    if lesson_context:
        pathway_context['current_lesson'] = {
            'id': lesson_context.get('id') or lesson_id,
            'title': lesson_context.get('title'),
        }

    code_ctx = CodeContext(
        code=code or "",
        error_log=error_log,
        problem_id=problem_id,
        track=(problem.get('track') if problem else None),
        skills_involved=list(problem.get('skills', [])) if problem else [],
        previous_attempts=len(recent_submissions),
        hints=list(problem.get('hints', [])) if problem else [],
        editorial=problem.get('editorial') if problem else None,
        solution_code=problem.get('solution_code') if problem else None,
    )

    # Build passport state
    passport_ctx = PassportState()
    if passport:
        passport_ctx.demonstrated_skills = list(passport.get("demonstrated_skills", []))
        passport_ctx.developing_skills = list(passport.get("developing_skills", []))
        passport_ctx.not_started_skills = list(passport.get("not_started_skills", []))
        passport_ctx.mastered_skills = list(passport.get("mastered_skills", []))
    else:
        try:
            skill_states = get_user_all_skill_states(user_id) if user_id else {}
        except Exception:
            skill_states = {}
        for skill_id, state in (skill_states or {}).items():
            status = (state or {}).get("status", "NOT_STARTED")
            if status == "DEMONSTRATED":
                passport_ctx.demonstrated_skills.append(skill_id)
            elif status == "DEVELOPING":
                passport_ctx.developing_skills.append(skill_id)
            elif status == "NOT_STARTED":
                passport_ctx.not_started_skills.append(skill_id)
            elif status == "MASTERED":
                passport_ctx.mastered_skills.append(skill_id)

    return TutorContext(
        code=code_ctx,
        passport=passport_ctx,
        stage=1,
        error_summary=(error_log[:200] if error_log else None),
        socratic_guardrail=True,
        recent_submissions=list(recent_submissions),
        lesson_context=lesson_context,
        pathway_context=pathway_context,
    )


def generate_hint_stage(
    stage: int,
    tutor_context: TutorContext,
) -> str:
    """Generate a hint at the specified stage of the progressive hinting engine.

    This is the **5-stage progressive hinting engine** (M5.2) that reveals
    guidance progressively without exposing the solution prematurely.

    Stage progression:
    1. Concept - High-level concept focus
    2. Approach - Suggested problem decomposition
    3. Edge Cases - Boundary condition considerations
    4. Pseudocode - Algorithm in plain language
    5. Editorial - Reference solution with explanations

    Args:
        stage: Hint stage number (1-5).
        tutor_context: The assembled TutorContext with code, errors, and passport.

    Returns:
        Hint text appropriate for the current stage.
    """
    if stage < 1 or stage > 5:
        raise ValueError(f"Hint stage must be 1-5, got {stage}")

    # Stage 1: Concept - focus on the core problem (Socratic)
    if stage == 1:
        if tutor_context.code.hints:
            return tutor_context.code.hints[0]
        skills = ", ".join(tutor_context.code.skills_involved) or "programming"
        domain = (tutor_context.pathway_context or {}).get('active_domain')
        track = (tutor_context.code.track or '').lower()
        pid = (tutor_context.code.problem_id or '').lower()
        is_ml = (
            domain == DOMAIN_MACHINE_LEARNING
            or track == 'machine-learning'
            or pid.startswith(('mle.', 'ml-'))
            or bool(_ml_concept_hint(skills))
        )
        extra = ''
        if is_ml:
            extra = _ml_concept_hint(skills)
        elif domain == DOMAIN_AI_ENGINEERING or track == 'ai-engineering':
            extra = _ai_concept_hint(skills)
        return (
            f"💡 *Concept hint:* This problem involves {skills}. "
            "Before coding, what is the input, what should the output represent, "
            f"and which concept connects them?{extra}"
        )

    # Stage 2: Approach - suggest decomposition
    if stage == 2:
        if len(tutor_context.code.hints) >= 2:
            return tutor_context.code.hints[1]
        skills = ", ".join(tutor_context.code.skills_involved) or "programming"
        return (
            "🧭 *Approach hint:* Try decomposing the problem into sub-problems. "
            "Can you identify 2-3 smaller tasks that, if solved individually, "
            "would combine to solve the whole problem?"
        )

    # Stage 3: Edge cases - boundary considerations (Socratic)
    if stage == 3:
        if len(tutor_context.code.hints) >= 3:
            hint = tutor_context.code.hints[2]
            if tutor_context.error_summary:
                hint += f"\n\nYour recent run reported: {tutor_context.error_summary}"
            return hint
        skills = ", ".join(tutor_context.code.skills_involved) or "programming"
        domain = (tutor_context.pathway_context or {}).get('active_domain')
        track = (tutor_context.code.track or '').lower()
        pid = (tutor_context.code.problem_id or '').lower()
        is_ml = (
            domain == DOMAIN_MACHINE_LEARNING
            or track == 'machine-learning'
            or pid.startswith(('mle.', 'ml-'))
            or bool(_ml_edge_case_hint(skills))
        )
        domain_extra = _ml_edge_case_hint(skills) if is_ml else ""
        question = " Which boundary input would you test first?"
        if domain == DOMAIN_AI_ENGINEERING or track == 'ai-engineering':
            question = " Which failure case or unsafe input would you test first?"
        return (
            "⚠️ *Edge case hint:* Consider boundary inputs and failure cases: empty or "
            "unexpected inputs, extreme values, and states that break assumptions. "
            f"Does your approach handle them correctly?{domain_extra}{question}"
        )

    # Stage 4: Pseudocode - algorithm in plain language (Socratic)
    if stage == 4:
        skills = ', '.join(tutor_context.code.skills_involved) or 'the main task'
        domain = (tutor_context.pathway_context or {}).get('active_domain')
        track = (tutor_context.code.track or '').lower()
        pid = (tutor_context.code.problem_id or '').lower()
        is_ml = (
            domain == DOMAIN_MACHINE_LEARNING
            or track == 'machine-learning'
            or pid.startswith(('mle.', 'ml-'))
            or bool(_ml_pseudocode_hint(skills))
        )
        domain_extra = _ml_pseudocode_hint(skills) if is_ml else ""
        extra_block = f"\n{domain_extra.strip()}" if domain_extra else ""
        return (
            f"📝 *Pseudocode hint:* For {skills}, outline the algorithm in plain language:\n"
            "1. Identify the input, assumptions, and the result required.\n"
            "2. Set up the state/data you need.\n"
            "3. Process each relevant case and update that state.\n"
            "4. Return/check the result on a normal case and a boundary case."
            f"{extra_block}\nCan you translate each step into your own code?"
        )

    # Stage 5: Editorial - reference solution
    if stage == 5:
        if tutor_context.code.editorial or tutor_context.code.solution_code:
            return (
                f"📖 *Editorial:*\n{tutor_context.code.editorial or ''}\n\n"
                f"```python\n{tutor_context.code.solution_code or ''}\n```"
            ).strip()
        return (
            "📖 *Editorial:* The reference solution implements the core pattern. "
            "Read through each decision and explain it in your own words. "
            "Key patterns to notice: initialization, iteration, conditionals, "
            "and final return values."
        )

    return ""


def save_tutor_conversation(
    user_id: int,
    role: str,
    content: str,
    lesson_id: Optional[str] = None,
) -> TutorConversation:
    """Save a tutor conversation entry to the database for persistence across sessions.

    Args:
        user_id: The learner's user ID.
        role: The speaker role ('user' or 'assistant').
        content: The conversation content/msg text.
        lesson_id: Optional lesson ID if conversation is lesson-specific.

    Returns:
        The saved TutorConversation model instance.
    """
    from app.models import db

    conversation = TutorConversation(
        user_id=user_id,
        lesson_id=lesson_id,
        role=role,
        content=content,
    )
    db.session.add(conversation)
    db.session.commit()
    return conversation


def load_tutor_conversation_history(
    user_id: int,
    lesson_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load conversation history from the database for a user and optional lesson.

    Args:
        user_id: The learner's user ID.
        lesson_id: Optional lesson ID to filter conversation to a specific lesson.

    Returns:
        List of conversation entries as dicts with 'role' and 'content' keys,
        ordered by creation time (oldest first).
    """
    from app.models import TutorConversation

    query = TutorConversation.query.filter_by(user_id=user_id)
    if lesson_id:
        query = query.filter_by(lesson_id=lesson_id)
    conversation_entries = query.order_by(TutorConversation.created_at.asc()).all()

    return [
        {
            'role': entry.role,
            'content': entry.content,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
        }
        for entry in conversation_entries
    ]


def diagnose_knowledge_gaps(tutor_context: TutorContext) -> Dict[str, Any]:
    """Identify likely concept gaps from the learner's current context.

    This helps the tutor identify what specific concepts the learner is
    struggling with, rather than just answering questions.

    Args:
        tutor_context: The assembled TutorContext.

    Returns:
        Dict with diagnosed gaps, suggested starting stage, and relevant
        skill nodes from the passport.
    """
    gaps = []
    suggested_stage = 0
    relevant_skills = []

    # Check error log for patterns
    if tutor_context.code.error_log:
        error_summary = tutor_context.error_summary or ""
        # Extended pattern detection for common Python errors
        patterns: List[tuple] = [
            (r"index out of range", "array/index boundary handling", 3),
            (r"syntaxerror", "python syntax fundamentals", 1),
            (r"invalid syntax", "python syntax fundamentals", 1),
            (r"name error", "variable scope/naming", 1),
            (r"typeerror", "type handling and conversion", 2),
            (r"keyerror", "dictionary key access", 2),
            (r"attributeerror", "object attribute access", 2),
            (r"valueerror", "value validation and range", 2),
            (r"zerodivisionerror", "division and zero checks", 2),
            (r"import error", "module import issues", 1),
        ]
        # ML-specific error and concept patterns
        ml_patterns: List[tuple] = [
            (r"division by zero|zero division", "statistics: division by zero in metric or mean", 2),
            (r"empty.*list|list.*empty", "data preparation: handling empty input", 2),
            (r"mean|average|std|standard deviation", "statistics: descriptive statistics", 1),
            (r"precision|recall|f1|confusion", "classification: evaluation metrics", 1),
            (r"overfit|underfit", "model evaluation: bias-variance diagnosis", 2),
            (r"forward|sigmoid|neural", "deep learning: forward propagation", 2),
        ]
        for pattern, gap_name, stage in patterns:
            if re.search(pattern, error_summary, re.IGNORECASE):
                gaps.append(gap_name)
                suggested_stage = min(suggested_stage or stage, stage)
                relevant_skills.extend(
                    tutor_context.passport.not_started_skills
                )
        for pattern, gap_name, stage in ml_patterns:
            if re.search(pattern, error_summary, re.IGNORECASE):
                gaps.append(gap_name)
                suggested_stage = min(suggested_stage or stage, stage)
                relevant_skills.extend(
                    tutor_context.passport.not_started_skills
                )

    # Check passport state for undeveloped skills
    if tutor_context.passport.not_started_skills:
        gaps.append(
            f"starting {len(tutor_context.passport.not_started_skills)} "
            f"skill{'s' if len(tutor_context.passport.not_started_skills) > 1 else ''}"
        )
        suggested_stage = min(suggested_stage or 1, 1)

    if tutor_context.passport.developing_skills:
        gaps.append(
            f"developing {len(tutor_context.passport.developing_skills)} "
            f"skill{'s' if len(tutor_context.passport.developing_skills) > 1 else ''}"
        )
        suggested_stage = max(suggested_stage, 2)  # Approach stage

    failed_attempts = [
        item for item in tutor_context.recent_submissions
        if item.get('verdict') not in {'ACCEPTED', 'PENDING', 'RUNNING'}
    ]
    if failed_attempts:
        gaps.append(
            f"reviewing {failed_attempts[-1].get('verdict', 'a recent attempt').lower()}"
        )
        suggested_stage = max(suggested_stage, 2)

    # If many edge case issues, bump to stage 3
    if len(gaps) > 2 and suggested_stage < 3:
        suggested_stage = 3
    if not suggested_stage:
        suggested_stage = 1

    return {
        "diagnosed_gaps": gaps or ["no specific gaps identified - keep practicing"],
        "suggested_starting_stage": suggested_stage,
        "relevant_skills": list(set(relevant_skills)),
        "passport_state": {
            "demonstrated": len(tutor_context.passport.demonstrated_skills),
            "developing": len(tutor_context.passport.developing_skills),
            "not_started": len(tutor_context.passport.not_started_skills),
            "mastered": len(tutor_context.passport.mastered_skills),
        },
    }