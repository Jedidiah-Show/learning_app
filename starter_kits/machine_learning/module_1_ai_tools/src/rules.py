"""Your written decision rules.

Write one dict per named rule in ``RULES``. Every dict has exactly these
three keys:

``name``
    a short name for the rule, for example ``"late_delivery"``.
``when``
    the condition the rule checks, written in plain words.
``then``
    the decision the rule produces: ``"approve"``, ``"review"``, or
    ``"decline"``.

The order of the list is the order the rules are checked in, and the first
rule that matches a request wins. The starter kit ships an empty list on
purpose: write at least three rules that reproduce the rule table in
README.md, and keep them in the same order as that table.

The fallback, the decision for a request that matches no rule, lives in
``decide()`` in ``src/automation.py``.
"""

RULES = []
