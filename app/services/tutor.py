"""AI Tutor 2.0 - Context-aware instructional guidance engine.

Provides Socratic hinting, knowledge gap diagnosis, and context-aware
responses spanning execution errors, recent submissions, and skill passport
state. Features a 5-stage progressive hinting engine for practice troubleshooting.
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from app.models import TutorConversation


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
    """Assemble complete tutor context from all available sources.

    This is the **Context Injector** (M5.1) that feeds user submission history,
    current code diffs, execution errors, and skill passport state into the
    tutor's context window.

    Args:
        user_id: The learner's user ID.
        lesson_id: Current lesson ID (if lesson-specific tutoring).
        problem_id: Current problem ID (if problem-specific tutoring).
        code: Current code the learner is working on.
        error_log: Recent execution error output.
        recent_submissions: Recent submission verdicts and metrics.
        passport: Learner's Skill Passport state.

    Returns:
        TutorContext ready to be fed into the LLM context window.
    """
    from app.services.skill_passport import (
        get_user_all_skill_states,
    )

    recent_submissions = recent_submissions or []
    if user_id and not recent_submissions:
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

    problem = None
    if problem_id:
        from app.practice_arena import all_arena_problems
        problem = all_arena_problems().get(problem_id)

    lesson_context = {}
    if lesson_id:
        from app.curriculum import get_lesson
        lesson = get_lesson(lesson_id)
        if lesson:
            lesson_context = {
                key: lesson[key]
                for key in ('title', 'outcomes', 'core_concepts', 'common_mistakes')
                if lesson.get(key)
            }

    code_ctx = CodeContext(
        code=code or "",
        error_log=error_log,
        problem_id=problem_id,
        track=problem.get('track') if problem else None,
        skills_involved=list(problem.get('skills', [])) if problem else [],
        previous_attempts=len(recent_submissions),
        hints=list(problem.get('hints', [])) if problem else [],
        editorial=problem.get('editorial') if problem else None,
        solution_code=problem.get('solution_code') if problem else None,
    )

    # Build passport state
    passport_ctx = PassportState()

    if passport:
        passport_ctx.demonstrated_skills = passport.get(
            "demonstrated_skills", []
        )
        passport_ctx.developing_skills = passport.get(
            "developing_skills", []
        )
        passport_ctx.not_started_skills = passport.get(
            "not_started_skills", []
        )
        passport_ctx.mastered_skills = passport.get(
            "mastered_skills", []
        )
    else:
        # Query from database
        skill_states = get_user_all_skill_states(user_id) if user_id else {}
        for skill_id, state in skill_states.items():
            status = state.get("status", "NOT_STARTED")
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
        error_summary=error_log[:200] if error_log else None,
        socratic_guardrail=True,
        recent_submissions=list(recent_submissions),
        lesson_context=lesson_context,
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

    # Stage 1: Concept - focus on the core problem
    if stage == 1:
        if tutor_context.code.hints:
            return tutor_context.code.hints[0]
        skills = ", ".join(tutor_context.code.skills_involved) or "programming"
        return (
            f"💡 *Concept hint:* This problem involves {skills}. "
            f"Focus on what you're being asked to compute or produce. "
            f"What is the input, and what should the output represent?"
        )

    # Stage 2: Approach - suggest decomposition
    if stage == 2:
        if len(tutor_context.code.hints) >= 2:
            return tutor_context.code.hints[1]
        return (
            "🧭 *Approach hint:* Try decomposing the problem into sub-problems. "
            "Can you identify 2-3 smaller tasks that, if solved individually, "
            "would combine to solve the whole problem?"
        )

    # Stage 3: Edge cases - boundary considerations
    if stage == 3:
        if len(tutor_context.code.hints) >= 3:
            hint = tutor_context.code.hints[2]
            if tutor_context.error_summary:
                hint += (
                    f"\n\nYour recent run reported: "
                    f"{tutor_context.error_summary}"
                )
            return hint
        return (
            "⚠️ *Edge case hint:* Consider what happens with boundary inputs: "
            "empty lists, single-element inputs, maximum values, or negative numbers. "
            "Does your code handle these cases correctly?"
        )

    # Stage 4: Pseudocode - algorithm in plain language
    if stage == 4:
        skills = ', '.join(tutor_context.code.skills_involved) or 'the main task'
        return (
            f"📝 *Pseudocode hint:* For {skills}, write the algorithm in plain "
            "language before coding:\n"
            "1. Identify the input and the result the problem asks for.\n"
            "2. Set up the state or data structure you need.\n"
            "3. Process each relevant input item and update that state.\n"
            "4. Return the result, then check it against an empty and a boundary input."
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
        for pattern, gap_name, stage in patterns:
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