# Archived migration

`1a7665109d7c_drop_pathway_destination_column.py.disabled` is the original,
unapplied draft that would have dropped `course_plan.pathway_destination`.

It was moved out of `migrations/versions/` during the pre-push migration-head
reconciliation. It was **not** executed and its content is preserved verbatim
with a `.disabled` suffix so Alembic cannot discover it accidentally.

Reason: `CoursePlan.pathway_destination` is still declared in `app/models.py`,
is read by `destination_for()` / the template context, and is checked by
`app/integrations.py::REQUIRED_COLUMNS`. Applying the draft would introduce an
immediate model/schema mismatch and discard learner focus data.

See `docs/MIGRATION_HEAD_RECONCILIATION.md` for the decision, verification and
the process for introducing a real cleanup migration later.
