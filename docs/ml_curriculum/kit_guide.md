# Starter kit authoring guide (ML pathway projects)

Every pathway module project ships a starter kit. The kit is what makes a
project claim checkable: the learner receives a stub with the exact function
signatures, a dataset they can use, and a test file whose assertions define
the contract. The server re-checks the same contract when the project is
submitted.

## Directory layout

```
starter_kits/machine_learning/<kit_dir>/
├── README.md                    # the brief the learner reads first
├── pyproject.toml               # package name, deps, pytest config
├── .gitignore
├── .github/workflows/tests.yml  # CI that runs pytest on push
├── data/<file>                  # the bundled dataset (small, synthetic, redistributable)
├── src/<module>.py              # learner stub: the functions to implement + build_report()
└── tests/test_<module>.py       # the checks that define the contract
```

`<kit_dir>` is given in the module spec. `<module>` is the module name; the
reference solution must be written to
`tests/ml_reference/<module>.py` with the same import name.

## Rules for `src/<module>.py`

- Public functions raise `NotImplementedError` with a message that says what
  to do. The learner fills them in.
- Docstrings state the contract precisely: the input shape, the output shape,
  and the file the function reads or writes.
- No side effects at import time. Reading a data file inside a function is
  fine.
- The module ends with `if __name__ == '__main__':` printing the report as
  JSON, so the learner can paste it into the submission form.

## Rules for `tests/test_<module>.py`

- One test per group of related assertions, named after the behaviour
  (`test_...`).
- Assertions use the exact expected values from the module spec.
- Tests read only files inside the kit (bundled data and the learner's
  artifacts).
- Tests never assert on anything the learner cannot control (wall-clock time,
  network, machine paths).

## Rules for `build_report()`

- Returns a `dict` whose keys are **exactly** the keys in the module spec's
  `report_contract`, with the same types.
- Deterministic: the same repository always produces the same report. No
  random seeds without a fixed value, no clock reads, no network.
- **Evidence, not claims.** Wherever it is possible, compute the value from
  the learner's own artifacts (their predictions file, their metrics file,
  their rules table) instead of hard-coding a number. A learner who did not
  do the work must not be able to produce a passing report.
- Values the learner must supply (for example "the name of the dataset you
  used") are read from a file the learner writes, not typed into the report
  function by the kit.

## CI workflow

Copy the pattern from an existing kit
(`starter_kits/machine_learning/module_1/.github/workflows/tests.yml`):

```yaml
name: <kit name>

on:
  push:
  pull_request:

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: python -m pip install -e '.[dev]'
      - run: pytest
```

`pyproject.toml` must pin its dependencies exactly (as the existing kits do)
and declare `[tool.pytest.ini_options]` with `pythonpath = ["src"]` and
`testpaths = ["tests"]`.

## Reference solution

`tests/ml_reference/<module>.py` is a complete, working implementation of the
same module. It exists so the repository can prove that the kit is
satisfiable: `tests/test_ml_starter_references.py` runs the kit's own test
file against the reference implementation and then checks the reference report
against the server-side contract.

- Same public functions and same behaviour as the kit expects.
- Same output files, same formats.
- No changes to the kit's tests to make the reference pass.
- Keep it short and readable: it is a teaching reference, not a framework.

## Dataset rules

- Small enough to read (usually 12–40 rows), synthetic, and free of personal
  data, so it can be redistributed inside the repository.
- Document every column in the kit README.
- The dataset must be fixed: the server contract and the kit tests agree on
  its exact contents.
