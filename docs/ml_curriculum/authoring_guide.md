# Lesson authoring guide (ML pathway)

This guide is the contract between the curriculum spec and the authored
content. Any lesson file that does not follow it will be rejected by the
validator in `docs/ml_curriculum/validate_content.py`.

## Audience

The learner has **zero prior knowledge**. Assume no programming, no statistics,
no algebra. The learner may have never opened a terminal.

Therefore every lesson must:

1. **Define a term the first time it appears**, in the same sentence, in plain
   words. "A *feature* is one column of your table — a single measurement you
   give the model."
2. **Use concrete numbers**, not abstractions. Prefer "the price was 120,000
   and the model predicted 112,000" over "the model performed reasonably".
3. **Show the working**. If you claim a mean is 4, show the sum and the count.
4. **Say why it matters** before the mechanics: what decision changes because
   the learner knows this?
5. **Warn about the mistake** a beginner actually makes here.
6. **Never assume a tool the learner has not met.** In the first module, say
   what a terminal, a notebook cell, and a repository are.

Short sentences. One idea per paragraph. Avoid: "obviously", "simply", "just
use", "as we saw earlier" (nothing was seen earlier), and any acronym that is
not expanded on first use.

## Lesson schema

```json
{
  "id": "mle.tools.01",
  "title": "What AI, machine learning, and deep learning mean",
  "status": "ready",
  "study_minutes": 40,
  "goal": "One sentence, learner-facing, describing what the learner can do after this lesson.",
  "sections": [
    {
      "heading": "A short heading that names the idea",
      "body": [
        "First paragraph: explain the idea with a concrete example.",
        "Second paragraph: add the detail, the limitation, or the beginner mistake."
      ]
    }
  ],
  "task": "A hands-on task the learner finishes in this session, with explicit inputs and expected output.",
  "quiz": {
    "questions": [
      {
        "id": "q1",
        "question": "A single clear question with exactly one defensible answer.",
        "choices": ["option A", "option B", "option C", "option D"],
        "answer": 2,
        "explanation": "Why the answer is right, and why the tempting wrong option is wrong. Written so that reading it teaches the concept."
      }
    ]
  }
}
```

Rules the validator enforces:

- `sections`: 3–5 entries. Each `body` has 2–3 paragraphs. Each paragraph is
  45–130 words. No bullet lists inside `body` (the lesson body is prose; use
  prose sentences instead of markdown lists).
- `task`: one paragraph, 25–70 words, with concrete inputs and a concrete
  expected output. It must be answerable with the tools introduced so far.
- `quiz.questions`: exactly 3. Each has exactly 4 choices, a unique `answer`
  index inside the choices, and an `explanation` of 25–80 words that names the
  correct idea.
- Distractors must be **plausible mistakes a beginner would actually make**,
  not obviously silly options. Never use "None of the above", "All of the
  above", or filler options such as "It depends".
- The three questions must test three different things: one about the concept,
  one about reading/working with the numbers or code in the lesson, and one
  about choosing the right method or spotting the beginner mistake.
- `study_minutes`: 30–60.

## Accuracy rules

- Every number in a lesson must be internally consistent. If the mean of
  2, 3, 3, 4, 8 is used, the sum (20) and count (5) must be shown or derivable.
- If a lesson says "about 2.1", the underlying value must round to that.
- Code shown in a lesson must be valid Python 3.11+ and must not need any
  package beyond the standard library unless the lesson explicitly says which
  package to install.
- Do not invent API names, function names, or library behaviour. If you are not
  certain a library call exists, describe the idea in prose instead.
- Do not state that a method "guarantees" or "proves" anything. Use the correct
  hedging: "on this data", "in this example", "usually".

## Banned content

The validator fails a file containing any of these:

`TODO`, `TBD`, `FIXME`, `Lorem`, `lorem ipsum`, `placeholder`, `coming soon`,
`to be written`, `XXX`, `???`, `...` (as an ellipsis standing in for content),
`<insert`, `[insert`, `sample text`, `etc.`, `and so on`, `various`, `several
things`, `some text`, `content here`, `Add more`, `expand here`.

Also banned: any sentence that merely says content exists without teaching it
("In this lesson we will cover the basics of X. By the end you will
understand X."). The first sentence of a section must teach something.

## Module file format

Each authoring job writes one file to `docs/ml_curriculum/authored/<module_id>.json`:

```json
{
  "module_id": "mle.tools",
  "lessons": [ { "id": "...", ... } ]
}
```

Lesson objects are complete and standalone: the integrator copies them into
`app/data/machine_learning_pathway.json` without editing. Keep the `id` exactly
as the spec gives it.
