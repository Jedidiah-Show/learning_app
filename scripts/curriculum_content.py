"""Curated additions for the upgraded RUACH AI Engineering curriculum.

The original PDF importer only knows the source PDF.  This module contains the
editorial additions that make the course beginner-accessible and current:
a Module 0 coding ramp, modern model-serving/agent lessons, practice exercises,
placement-check material, and resource links.

Keep content here rather than editing the generated JSON by hand.  The upgrade
script merges it idempotently and preserves the review overlay.
"""

from __future__ import annotations

from textwrap import dedent


MODULE_TITLES = {
    '00': 'AI Engineering Foundations',
    '01': 'Python for AI Engineers',
    '02': 'Backend Engineering',
    '03': 'LLM Fundamentals',
    '04': 'LLM Application Engineering',
    '05': 'RAG (Retrieval-Augmented Generation)',
    '06': 'AI Agents',
    '07': 'Agent Orchestration',
    '08': 'MCP (Model Context Protocol)',
    '09': 'Production AI Engineering',
    '10': 'Docker & Deployment',
    '11': 'AI System Design',
    '12': 'Final Capstone: Build and Review an AI System',
}


def _code(title: str, content: str, language: str, notice: list[str]) -> dict:
    return {
        'title': title,
        'code': dedent(content).strip(),
        'language': language,
        'what_to_notice': notice,
    }


def _lesson(
    lesson_id: str,
    module_id: str,
    title: str,
    subtitle: str,
    why: str,
    outcomes: list[str],
    concepts: list[tuple[str, str]],
    terms: list[tuple[str, str]],
    mental_model: str,
    example: str,
    steps: list[str],
    code: dict,
    mistakes: list[str],
    production: list[str],
    checklist: list[str],
    questions: list[str],
    tasks: list[str],
    capstone: str,
    beginner_tip: str,
    answers: list[str],
) -> dict:
    return {
        'id': lesson_id,
        'module_id': module_id,
        'title': title,
        'subtitle': subtitle,
        'why_it_matters': [why],
        'outcomes': outcomes,
        'core_concepts': [
            {'title': concept_title, 'content': concept_text}
            for concept_title, concept_text in concepts
        ],
        'key_terms': [
            {'term': term, 'definition': definition}
            for term, definition in terms
        ],
        'mental_model': mental_model,
        'worked_example': [example],
        'steps': steps,
        'code': code,
        'common_mistakes': mistakes,
        'production_notes': production,
        'checklist': checklist,
        'questions': questions,
        'tasks': tasks,
        'capstone': capstone,
        'beginner_tip': beginner_tip,
        '_answers': answers,
    }


LESSONS = [
    _lesson(
        '0.06',
        '00',
        'Your first Python program',
        'Write, run, and debug a tiny Python script without guessing what the computer is doing.',
        'The fastest way to stop feeling lost is to run a program you can see, change, and break. This lesson gives you the smallest complete loop: edit a file, run it, read the output, and fix one error.',
        [
            'Create a Python file and run it from a terminal with an explicit interpreter.',
            'Store values in variables and format readable output with f-strings.',
            'Use a traceback to find the line where a program failed.',
        ],
        [
            (
                'A program is a list of instructions',
                'Python runs a script from top to bottom. Each line can calculate a value, call a function, or make a decision. print() writes a value to the terminal so you can see what happened. A variable is just a name attached to a value; it is not a box with a fixed type.',
            ),
            (
                'Strings, numbers, and f-strings',
                'Text lives inside quotes and numbers do not. The + operator joins strings, but it does not mix strings and numbers automatically. An f-string starts with f and puts expressions inside braces: f"Total: {total:.2f}". The .2f part asks for two decimal places.',
            ),
            (
                'Errors are feedback, not failure',
                'A SyntaxError means Python could not understand the file; a NameError means a name was used before it existed; a TypeError means two values could not be combined. Read the last line of the traceback first, then the line number, then the source line. Change one thing and run again.',
            ),
        ],
        [
            ('Script', 'A text file containing Python instructions that an interpreter runs from top to bottom.'),
            ('Interpreter', 'The program (python3 on most systems) that reads and executes Python code.'),
            ('Variable', 'A name that refers to a value so the rest of the program can reuse it.'),
            ('f-string', 'A string prefixed with f that inserts expressions inside braces.'),
            ('Traceback', 'The report Python prints when an error stops the program, including the failing line and call path.'),
        ],
        'Running a script is like following a recipe: the interpreter reads one step at a time, and the traceback points to the step where the kitchen caught fire.',
        'A learner writes price = "0.50", quantity = 3, and total = price * quantity. Python repeats the text three times because price is a string. They change the value to float(price), print f"Total: {total:.2f}", and the output becomes 1.50. The lesson is not the arithmetic; it is checking the type before trusting the result.',
        [
            'Create a folder for the course and open a terminal inside it.',
            'Create hello.py with a variable, an f-string, and one print call.',
            'Run python3 hello.py and read the output before changing anything.',
            'Remove a quote mark on purpose, run the file, and identify the line and error type.',
            'Restore the quote, change one value, and run it again.',
        ],
        _code(
            'A complete first script: values in, one calculation, formatted output.',
            '''
            name = "Ada"
            tickets = 3
            price_per_ticket = 12.5

            total = tickets * price_per_ticket
            print(f"{name} bought {tickets} tickets for {total:.2f}")
            ''',
            'python',
            [
                'Variables do not need type declarations, but the values still have types. price_per_ticket is a float, so multiplication produces a float.',
                'The f-string formats the number only for display. It does not change the value stored in total.',
                'If the multiplication used a string price, Python would repeat text instead of doing arithmetic.',
            ],
        ),
        [
            'Forgetting quotation marks around text, which produces a NameError for each bare word.',
            'Joining a string and a number with + instead of using an f-string or str().',
            'Changing several lines at once after an error, so you cannot tell which change fixed it.',
        ],
        [
            'Keep runnable scripts in files and commit them; a notebook cell that depends on hidden state is not reproducible.',
            'Run the same interpreter you use in CI. python3 hello.py is more explicit than a double-click.',
            'Never put API keys in a first script. Read secrets from environment variables when you reach the HTTP lesson.',
        ],
        [
            'I can create a .py file and run it with python3.',
            'I can explain what a variable and an f-string do.',
            'I can read the last line of a traceback and find the failing line.',
            'I know the difference between a string and a number.',
            'I saved my first script in the course repository.',
        ],
        [
            'What is the difference between the name of a variable and the value it refers to?',
            'Why does "3" * 2 produce "33" instead of 6?',
            'Which part of a traceback tells you where to look first?',
            'Why is it useful to change only one thing after an error?',
            'What does the :.2f format specifier do?',
            'Why should a first script live in a file instead of only in a REPL?',
        ],
        [
            'Write and run a script that prints your name, the number of lessons you plan to finish this week, and a formatted total study time (25 minutes).',
            'Break the script with a missing quote and a wrong type, then write down the error type and line number for each (20 minutes).',
            'Commit the working script with the message "Add first Python script" (10 minutes).',
        ],
        'Every capstone begins with a script a reviewer can run. Keep this file in notes/ and link it from your Module 0 project evidence.',
        'Type every example yourself. Small typing mistakes are part of learning to debug.',
        [
            'A variable is a name that refers to a value; the value has a type.',
            'Multiplication repeats a string when one operand is text, so convert it with float() first.',
            'Read the final error line, then the line number in the traceback.',
            'Changing one thing at a time lets you know which change fixed the error.',
            'It formats a number with two digits after the decimal point for display.',
            'A file can be rerun, reviewed, committed, and shared without hidden state.',
        ],
    ),
    _lesson(
        '0.07',
        '00',
        'Lists, dictionaries, and loops',
        'Organise several values, look them up by name, and process them without repeating yourself.',
        'AI APIs return lists of choices and dictionaries of fields. If you can loop over them and pick values safely, you can turn raw responses into useful data instead of copying values by hand.',
        [
            'Create lists and dictionaries and access values by position or key.',
            'Use a loop to transform every item in a collection.',
            'Use .get() and validation to avoid a KeyError on missing fields.',
        ],
        [
            (
                'Lists keep order',
                'A list is written with square brackets: ["read", "write", "delete"]. Indexing starts at zero, and a slice such as items[1:3] returns a new list. Use a list when order or duplicates matter.',
            ),
            (
                'Dictionaries look up by key',
                'A dictionary maps keys to values: {"name": "Atlas", "price": 0.5}. Access a known key with data["name"]; use data.get("price", 0.0) when the field may be absent. Keys must be hashable, so a list cannot be a key.',
            ),
            (
                'Loops turn one item into many',
                'A for loop visits each item: for model in models: print(model["name"]). A comprehension builds a new collection in one expression: [model["name"] for model in models]. Both are fine; choose the one a reviewer can read.',
            ),
        ],
        [
            ('List', 'An ordered, mutable collection written with square brackets.'),
            ('Dictionary', 'A mutable mapping from keys to values written with curly braces.'),
            ('KeyError', 'The error raised when code asks a dictionary for a key it does not contain.'),
            ('Iteration', 'Processing each item in a collection, usually with a for loop.'),
            ('Comprehension', 'A compact expression that builds a list or dictionary from an iterable.'),
        ],
        'A list is a queue of parcels; a dictionary is the address label on each parcel. A loop is the courier who visits every parcel once.',
        'Mira receives a model catalogue as a list of dictionaries. One provider is missing a price, so a direct row["price"] crashes the whole report. She changes it to row.get("price"), skips rows with no price, and counts the skipped rows. The output now tells the reader how many rows were priced instead of silently averaging over an empty list.',
        [
            'Create a list of three dictionaries, each with a name and a numeric price.',
            'Print one field with brackets and one with .get().',
            'Loop over the list and print the name and price together.',
            'Build a dictionary from names to prices with a comprehension.',
            'Add a missing key and confirm .get() prevents a crash, then log the missing value.',
        ],
        _code(
            'Loop, lookup, and comprehension over a small model catalogue.',
            '''
            models = [
                {"name": "Atlas", "price": 0.5},
                {"name": "Kestrel", "price": 1.2},
            ]

            for model in models:
                print(model["name"], model["price"])

            names = [model["name"] for model in models]
            prices = {model["name"]: model["price"] for model in models}
            print(names, prices["Atlas"])
            ''',
            'python',
            [
                'The loop reuses the same two field names for every record, so the output shape stays predictable.',
                'The dictionary comprehension assumes names are unique; a duplicate name would silently overwrite the earlier price.',
                'Bracket access is appropriate when the key is required. Use .get() when absence is a valid state you will handle.',
            ],
        ),
        [
            'Using a list where a key lookup is needed, then searching the list on every request.',
            'Assuming a dictionary key exists and crashing an entire batch when one record is incomplete.',
            'Mutating a list while looping over it, which skips items or duplicates work.',
        ],
        [
            'Validate collection shape at the boundary and convert it into a typed record before business logic uses it.',
            'Log counts for records read, kept, and skipped; an average over zero records is an outage disguised as a zero.',
            'Keep loops small enough that each one has one reason to change.',
        ],
        [
            'I can create a list and a dictionary from memory.',
            'I can access a list item by index and a dictionary value by key.',
            'I use .get() when a key may be absent.',
            'I can write a loop and a simple comprehension.',
            'I can explain why mutating a collection during iteration is risky.',
        ],
        [
            'When is a list a better choice than a dictionary?',
            'What happens when two records have the same name in a dictionary comprehension?',
            'Why does .get() return None instead of raising KeyError?',
            'How would you count skipped records in a loop?',
            'Why does a zero average over an empty list hide a data problem?',
            'Which is easier to review: a three-line comprehension or a named loop?',
        ],
        [
            'Build a catalogue of four models with name, provider, and price, then print the cheapest price (25 minutes).',
            'Add one record with a missing price and make the script report how many records were skipped (20 minutes).',
            'Rewrite one loop as a comprehension and explain which version you would review (15 minutes).',
        ],
        'The capstone catalogue and retrieval layers both move lists of records into dictionaries keyed by stable IDs. This is the same shape you will use again.',
        'Use names that say what the collection contains: models, prices, missing_rows. Short names save typing but cost understanding.',
        [
            'A list preserves order and allows duplicates; a dictionary looks up values by key.',
            'The later record overwrites the earlier value for that key.',
            'It returns the supplied default (or None) instead of raising an exception.',
            'Increment a counter in the branch where the record is skipped.',
            'It can mean every row was malformed, so the report should show counts or fail.',
            'A named loop is usually easier when the transformation has conditions or side effects.',
        ],
    ),
    _lesson(
        '0.08',
        '00',
        'Functions, inputs, and return values',
        'Turn repeated steps into a named function with a clear input and output.',
        'Functions are how you stop copying code and start making decisions testable. A small function with explicit inputs and a return value can be called by a script, a test, or an API handler without changing its internals.',
        [
            'Define a function with parameters and a return value.',
            'Validate inputs and raise a clear error when the contract is broken.',
            'Call a function from a script and test it with several inputs.',
        ],
        [
            (
                'A function is a named contract',
                'def total_cost(tickets, price): names the function and its inputs. The return statement hands a result back to the caller. A function that only prints is hard to test; return the value and let the caller decide how to display it.',
            ),
            (
                'Parameters are local names',
                'Parameters exist only while the function runs. Pass values in rather than reading globals, so the same function works in a script, a test, and a web request. Default values are useful for safe options, but never use a mutable default such as [] because it is shared between calls.',
            ),
            (
                'Fail loudly at the boundary',
                'Validate values before doing arithmetic: negative tickets, a non-numeric price, or a missing argument should raise ValueError or TypeError with a message that names the problem. A wrong answer returned silently is harder to debug than an exception.',
            ),
        ],
        [
            ('Function', 'A named block of code that accepts inputs and can return a result.'),
            ('Parameter', 'A name in a function definition that receives an argument when the function is called.'),
            ('Return value', 'The result a function hands back to its caller with return.'),
            ('ValueError', 'An exception raised when a value has the right type but an unacceptable value.'),
            ('Mutable default', 'A default argument such as [] or {} that is created once and shared across calls.'),
        ],
        'A function is a vending machine: you put in clearly labelled inputs, it validates them, and it returns one predictable output. Printing is not the same as returning.',
        'A support script calculates refunds inline in three places. One copy forgets to validate negative amounts, so a refund of -20 becomes a charge. The team extracts refund_total(amount, fee) with validation and a return value, then replaces all three copies with calls to it. The tests now cover one contract instead of three copies.',
        [
            'Write a function that takes two numbers and returns their sum.',
            'Call it from a print statement and from a variable assignment.',
            'Add validation that rejects a negative number with ValueError.',
            'Write a second function that calls the first and formats the result.',
            'Run the function with a normal value, a zero, and an invalid value.',
        ],
        _code(
            'A small function with validation, a return value, and a formatted caller.',
            '''
            def total_cost(tickets: int, price: float) -> float:
                if tickets < 0 or price < 0:
                    raise ValueError("tickets and price must be non-negative")
                return round(tickets * price, 2)


            def receipt(name: str, tickets: int, price: float) -> str:
                return f"{name}: {total_cost(tickets, price):.2f}"


            print(receipt("Ada", 3, 12.5))
            ''',
            'python',
            [
                'The type hints document the intended contract, but Python does not enforce them at runtime; the explicit checks do.',
                'The caller formats the result. Keeping formatting out of total_cost makes the calculation reusable in tests and APIs.',
                'Raising ValueError names the broken contract instead of returning a plausible but wrong number.',
            ],
        ),
        [
            'Printing inside a calculation function so callers cannot reuse the result.',
            'Using a mutable default such as items=[] and then appending to it across calls.',
            'Returning None on invalid input, forcing every caller to remember a special case.',
        ],
        [
            'Keep calculations pure and push display, logging, and network calls to the edges.',
            'Give every function one job and a name that describes the result, not the implementation.',
            'Write at least one test for the happy path, one boundary, and one invalid input.',
        ],
        [
            'I can define a function with parameters and a return value.',
            'I know the difference between printing and returning.',
            'I validate inputs before calculating.',
            'I avoid mutable default arguments.',
            'I can call the same function from a script and a test.',
        ],
        [
            'What does return do that print does not?',
            'Why is a mutable default argument dangerous?',
            'When should a function raise an exception instead of returning None?',
            'Why are type hints not enough to validate runtime input?',
            'What is a pure function, and why is it easier to test?',
            'How many responsibilities should a small function have?',
        ],
        [
            'Write a function that calculates a total with a discount and rejects negative inputs (20 minutes).',
            'Add a second function that formats the result, keeping calculation and display separate (15 minutes).',
            'Run the function with a normal value, a boundary value, and an invalid value, and record the output (15 minutes).',
        ],
        'Every module project will expose a small number of well-named functions that a reviewer can test. Start that habit here.',
        'If a function is hard to name, it probably does more than one thing. Split it before adding more code.',
        [
            'Returning hands a value back to the caller; printing only shows it on screen.',
            'The default list is created once and shared, so changes leak into later calls.',
            'Raise when the caller violated a contract or the result would be invalid; return None when absence is an expected state.',
            'Type hints are metadata for tools and readers, not runtime checks.',
            'A pure function depends only on its inputs and returns a value without side effects.',
            'Usually one, expressed by a name that describes the returned result.',
        ],
    ),
    _lesson(
        '0.09',
        '00',
        'Files, JSON, and the command line',
        'Read a file, parse JSON, and make a small script accept a path from the terminal.',
        'Most AI work starts with data on disk and configuration from the environment. Reading a file safely and decoding JSON without crashing are the first steps toward ingestion, evaluation, and reproducible experiments.',
        [
            'Read a text file with an explicit encoding.',
            'Decode JSON and validate the shape you expect.',
            'Pass a file path to a script with sys.argv and fail clearly when it is missing.',
        ],
        [
            (
                'Paths are objects, not strings',
                'pathlib.Path joins paths, checks existence, and reads text without manually concatenating slashes. Always pass encoding="utf-8" so the same file works on every machine. A relative path depends on the current working directory, which is why command-line tools should show the resolved path in an error.',
            ),
            (
                'JSON is text with rules',
                'json.loads(text) returns Python dictionaries, lists, strings, numbers, booleans, and None. It raises JSONDecodeError when the text is malformed. A successful decode does not prove the fields you need exist, so check the top-level type and required keys before using them.',
            ),
            (
                'Command-line scripts need a contract',
                'sys.argv[1] is the first argument after the script name. If it is missing, print a usage message and exit non-zero. A good script accepts a path, validates it, reports the number of records it read, and writes output to a predictable place.',
            ),
        ],
        [
            ('pathlib', 'The standard-library module for working with filesystem paths as objects.'),
            ('Encoding', 'The character mapping used to turn bytes into text; UTF-8 is the safe default for source and data files.'),
            ('JSONDecodeError', 'The exception raised when json.loads cannot parse malformed JSON text.'),
            ('Schema', 'The expected shape and types of a decoded object, checked before business logic uses it.'),
            ('argv', 'The list of command-line arguments available to a Python script.'),
        ],
        'A file is a sealed parcel, JSON is the packing list, and your script is the inspector: open it, check the label, and report exactly what is missing.',
        'A learner downloads an evaluation set and writes data = json.load(open("data.json")). It works on their laptop but fails in CI because the working directory differs, and a malformed file produces a long traceback with no filename. They switch to Path, add encoding, catch JSONDecodeError, and print the resolved path and record count. The next run fails with a useful message in one line.',
        [
            'Create a small JSON file with a name and a list of items.',
            'Write a script that takes the path as sys.argv[1] and prints the item count.',
            'Run it from the project root and from a different directory to see why paths matter.',
            'Break the JSON intentionally and print a clear error instead of a traceback.',
            'Commit the script and a sample file with no secrets.',
        ],
        _code(
            'A command-line JSON reader with an explicit path, encoding, and shape check.',
            '''
            import json
            import sys
            from pathlib import Path


            def summarize(path: Path) -> dict:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("expected a JSON object")
                items = data.get("items", [])
                if not isinstance(items, list):
                    raise ValueError("items must be a list")
                return {"name": data.get("name", ""), "items": len(items)}


            path = Path(sys.argv[1])
            print(summarize(path))
            ''',
            'python',
            [
                'Path.read_text handles opening and closing the file; you do not need a manual close call.',
                'The shape check is separate from decoding. Valid JSON can still be a list when the script expects an object.',
                'A real CLI should catch FileNotFoundError and JSONDecodeError and exit with a short message rather than a raw traceback.',
            ],
        ),
        [
            'Opening a file without an encoding, which works on one laptop and fails on another.',
            'Assuming every decoded JSON object has the fields the script expects.',
            'Hard-coding a personal path such as /Users/me/data.json into a shared script.',
        ],
        [
            'Report the resolved path, encoding, and record count when ingestion starts; this makes data incidents reproducible.',
            'Treat files as untrusted input: bound the size you read and validate the shape before loading everything into memory.',
            'Keep sample data small, licensed, and free of personal or secret values.',
        ],
        [
            'I can read a UTF-8 text file with pathlib.',
            'I can decode JSON and check the top-level type.',
            'I can pass a path on the command line and handle a missing argument.',
            'I know why a successful JSON decode does not prove the schema is correct.',
            'I committed a small sample file without secrets.',
        ],
        [
            'Why is an explicit encoding important even on a machine where the default works?',
            'What is the difference between a JSON syntax error and a schema error?',
            'Why does a relative path behave differently in a terminal and in CI?',
            'What should a CLI print when the file is missing?',
            'Why should a script report how many records it read?',
            'What would you check before loading a 2 GB JSON file into memory?',
        ],
        [
            'Create a JSON file with a name and five items, then write a script that prints the count (25 minutes).',
            'Add a malformed file and make the script print the filename and a one-line error (20 minutes).',
            'Run the script from a different working directory and record what you had to change (15 minutes).',
        ],
        'The capstone will ingest evaluation sets, policy documents, and configuration files. This small reader is the pattern you will harden later.',
        'Use a tiny sample file first. Debugging a parser on a 2 GB file is slow and unnecessary.',
        [
            'The default encoding differs across systems; explicit UTF-8 makes behaviour reproducible.',
            'Syntax errors mean the text is not JSON; schema errors mean the decoded value has the wrong shape or fields.',
            'Relative paths resolve against the current working directory, which changes between terminals, services, and CI.',
            'A short usage message naming the expected argument and exiting non-zero.',
            'The count separates an empty valid file from a parser that silently skipped rows.',
            'Check file size, required top-level keys, nesting depth, and whether streaming is needed.',
        ],
    ),
    _lesson(
        '0.10',
        '00',
        'Git and GitHub from zero',
        'Save snapshots of your work, write a useful commit message, and keep secrets out of history.',
        'AI projects change quickly: prompts, evaluation sets, and dependencies all move. Git gives you a reviewable history and a safe way to recover when an experiment breaks. GitHub adds a remote copy and a place to run automated checks.',
        [
            'Initialise a repository and make a first commit.',
            'Write a commit message that explains why a change exists.',
            'Keep secrets and generated files out of version control.',
        ],
        [
            (
                'A repository is a history of decisions',
                'git init creates a local repository. git status shows what changed, git add stages a file, and git commit records a snapshot with a message. A commit is not a backup of your whole computer; it is a reviewable diff plus the reason for it.',
            ),
            (
                'Commit messages are for future readers',
                'Start with a short imperative subject such as "Add JSON reader" and keep it under about 72 characters. Use the body to explain why the change was needed, what trade-off you made, and how you verified it. "Update stuff" forces the next reader to reverse-engineer your intent.',
            ),
            (
                'Never commit secrets or generated files',
                'A .gitignore lists files Git should not track: .env, .venv/, __pycache__/, and large model weights. Deleting a secret in a later commit does not remove it from history; rotate the credential and rewrite history only with a deliberate plan.',
            ),
        ],
        [
            ('Repository', 'A directory whose changes Git tracks as a history of commits.'),
            ('Commit', 'A snapshot of staged changes plus a message, author, and parent commit.'),
            ('Remote', 'A named copy of a repository hosted elsewhere, usually on GitHub.'),
            ('.gitignore', 'A file listing paths Git should not track.'),
            ('Pull request', 'A request to review and merge changes from one branch into another.'),
        ],
        'A commit is a labelled photograph of your project, not a video of everything you did. The message is the note on the back explaining why you took it.',
        'A learner commits a .env file with an API key, then deletes it in the next commit. The key still exists in the first commit and in every clone. They rotate the key, add .env to .gitignore, commit .env.example with empty values, and write a short note in the README. The fix is rotation and prevention, not a prettier diff.',
        [
            'Create a repository and run git status before adding anything.',
            'Add a .gitignore for .env, .venv/, and __pycache__/.',
            'Stage one file and commit it with a subject and a one-line reason.',
            'Create a GitHub repository and add it as a remote.',
            'Push the commit and confirm the file appears on GitHub.',
        ],
        _code(
            'The smallest safe Git workflow for a course project.',
            '''
            git init
            git add .gitignore hello.py
            git commit -m "Add first Python script" -m "Verifies the interpreter and prints a formatted total."
            git branch -M main
            git remote add origin https://github.com/your-name/ai-engineering-lab.git
            git push -u origin main
            ''',
            'bash',
            [
                'The commit has a short subject and a body separated by -m; the body records why the change exists.',
                'git add names the files explicitly, which makes it harder to commit a secret by accident.',
                'The remote URL is HTTPS here. Use a credential helper or SSH key; never paste a token into a command that will be saved in shell history.',
            ],
        ),
        [
            'Committing .env or a virtual environment because the repository is private.',
            'Mixing unrelated changes in one commit so a rollback removes more than intended.',
            'Force-pushing a shared branch and overwriting someone else\'s commits.',
        ],
        [
            'Protect the main branch with review and automated checks once you collaborate.',
            'Commit small changes with a reason and a verification note; future you is the main reader.',
            'Run a secret scan before pushing and rotate any credential that was ever committed.',
        ],
        [
            'I can initialise a repository and read git status.',
            'I can stage and commit one focused change.',
            'My .gitignore excludes secrets, virtual environments, and caches.',
            'I can push to a remote and see the commit on GitHub.',
            'I can explain why deleting a secret in a later commit is not enough.',
        ],
        [
            'What is the difference between the working tree, the staging area, and a commit?',
            'Why should a commit message describe why, not just what?',
            'What belongs in .gitignore for a Python AI project?',
            'Why does deleting a secret in a later commit fail to remove it from history?',
            'When is a force push acceptable?',
            'What does a remote add that a local repository does not have?',
        ],
        [
            'Create a repository, add a .gitignore, and commit your first script (20 minutes).',
            'Write a commit body that records the problem, the change, and how you checked it (15 minutes).',
            'Push to GitHub and confirm the repository contains no .env or virtual environment files (15 minutes).',
        ],
        'The capstone repository is the primary evidence for every project. A clean history and a readable README make the reviewer\'s job possible.',
        'If Git feels abstract, draw three boxes: working tree, staging area, repository. Every command moves changes between them.',
        [
            'The working tree is the files you edit; staging selects what goes into the next commit; a commit is the recorded snapshot.',
            'The why lets a future reader decide whether the change still applies.',
            'At minimum .env, .venv/, __pycache__/, and large generated artefacts.',
            'The old commit still contains the value and clones retain it; rotate the credential.',
            'Only on a branch you alone own, after coordinating, and never to erase evidence on a shared branch.',
            'A remote provides another copy and a collaboration point, but it does not replace review or backups.',
        ],
    ),
    _lesson(
        '0.11',
        '00',
        'HTTP and APIs from zero',
        'Ask another computer for data, check the status code, and handle the response without crashing.',
        'Almost every AI feature is a network client. Model providers, vector databases, and internal services all answer over HTTP. A missing timeout or an unchecked status code turns a small provider hiccup into a stuck worker.',
        [
            'Send a GET request with an explicit timeout and read the status code.',
            'Decode JSON only after checking that the response succeeded.',
            'Distinguish client errors, server errors, and retryable failures.',
        ],
        [
            (
                'A request is a typed message',
                'An HTTP request has a method, a URL, headers, and sometimes a body. A response has a status code, headers, and a body. Use GET for reads and POST for actions that create or change data. Put credentials in headers, never in the URL query string where logs record them.',
            ),
            (
                'Status codes are a contract',
                '2xx means the request succeeded; 3xx redirects; 4xx means the caller needs to change something; 5xx means the server failed. A 401 or 403 is a configuration problem, 404 is a missing resource, 422 is invalid input, and 429 asks you to slow down. Do not retry every non-2xx response.',
            ),
            (
                'Timeouts and retries are part of the design',
                'Set a connect timeout and a read timeout. Retry only transient failures such as 429, 500, 502, 503, 504, and network timeouts, with a cap and jitter. A non-idempotent write needs an idempotency key before it can be retried safely.',
            ),
        ],
        [
            ('HTTP', 'The request/response protocol used by web APIs.'),
            ('Status code', 'A three-digit number describing the outcome of an HTTP request.'),
            ('Timeout', 'A limit on how long a client waits for a connection or response.'),
            ('Idempotency key', 'A unique value that lets a server recognise a repeated write and avoid duplicating it.'),
            ('Retryable error', 'A temporary failure that may succeed if the request is attempted again.'),
        ],
        'An API call is a postal delivery: the address and package matter, but so do the delivery deadline and the tracking number you use when it does not arrive.',
        'A learner calls a model endpoint without a timeout. One stalled response holds a worker for six minutes, and their retry loop sends the same write three times. They add a 10-second timeout, check the status before decoding, retry only 429 and 5xx, and add an idempotency key. The next provider incident produces a fast, visible error instead of duplicate charges.',
        [
            'Send a GET request to a public API with a 10-second timeout.',
            'Print the status code, content type, and one field from the JSON body.',
            'Break the URL and observe a 404; use an invalid token and observe 401.',
            'Add a retry only for 429 and 5xx, capped at three attempts.',
            'Write down which failures should surface to the user immediately.',
        ],
        _code(
            'A minimal HTTP client with a timeout, status check, and JSON decode.',
            '''
            import httpx

            response = httpx.get(
                "https://api.example.com/v1/models",
                timeout=httpx.Timeout(10.0, connect=3.0),
                headers={"Authorization": "Bearer <token>"},
            )
            response.raise_for_status()
            payload = response.json()
            print(response.status_code, len(payload.get("data", [])))
            ''',
            'python',
            [
                'raise_for_status() turns 4xx and 5xx responses into exceptions before the code tries to decode a body that may be an error page.',
                'The connect timeout is shorter than the total timeout, so a dead host fails quickly while a slow response still has time.',
                'The token is a placeholder; real code reads it from configuration and never prints the header.',
            ],
        ),
        [
            'Calling an API without a timeout, so one stalled socket occupies a worker indefinitely.',
            'Decoding JSON before checking the status, which hides a useful error behind a parse failure.',
            'Retrying 401, 403, or 422 responses, which cannot succeed without a code or configuration change.',
        ],
        [
            'Log status, latency, retry count, and a provider request ID; alert on 5xx rate and p95, not only exceptions.',
            'Keep the total deadline below the caller\'s timeout and cancel downstream work when the caller disconnects.',
            'Validate the decoded response against a schema before it enters application logic.',
        ],
        [
            'I can send a GET request with a timeout.',
            'I check the status before decoding JSON.',
            'I know which status codes are worth retrying.',
            'I keep credentials in headers, not URLs.',
            'I can explain why a write needs an idempotency key before retrying.',
        ],
        [
            'What does a 200 status not prove about the response body?',
            'Which status codes should a client retry, and which should it surface?',
            'Why is a missing timeout dangerous even when the provider is usually fast?',
            'What is the difference between a connect timeout and a read timeout?',
            'Why does a retried POST need an idempotency key?',
            'What would you log to debug a p95 latency regression?',
        ],
        [
            'Call a public API with a timeout and print the status, content type, and one decoded field (25 minutes).',
            'Trigger a 404 and a 401, then write the user-facing message you would show for each (20 minutes).',
            'Add a capped retry for 429 and 5xx, and explain why you did not retry 422 (20 minutes).',
        ],
        'The capstone\'s model gateway is this lesson at production scale: timeouts, bounded retries, schema validation, and per-call cost and latency records.',
        'Do not test retries against a real provider. Use a local mock or a test double so you can control the status codes.',
        [
            'It proves the transport succeeded; the body may still be malformed or the wrong shape.',
            'Retry 429, 500, 502, 503, 504, and timeouts; surface 4xx configuration and validation errors.',
            'A stalled request can hold a worker until the client restarts, reducing capacity for everyone.',
            'Connect bounds the TCP/TLS handshake; read bounds waiting for response bytes.',
            'The server may have completed the first write, so a retry without a key can duplicate the effect.',
            'Status, latency, retry count, provider request ID, and the model or endpoint version.',
        ],
    ),
    _lesson(
        '3.16',
        '03',
        'Open-weight and self-hosted models',
        'Choose when an open-weight model, a managed API, or a self-hosted endpoint is the right trade-off.',
        'Open-weight models can reduce lock-in, keep data in your environment, and change the cost curve, but they add GPU capacity, evaluation, patching, and on-call work. The decision is an operating-model choice, not an ideology.',
        [
            'Distinguish open-weight from open-source and read the licence before committing.',
            'Estimate memory and throughput for a candidate model and quantization.',
            'Compare hosted and self-hosted options with quality, latency, cost, and operational evidence.',
        ],
        [
            (
                'Weights, licences, and control',
                'An open-weight model publishes trained parameters you can download, but the training data and code may not be open. The licence can restrict commercial use, redistribution, or acceptable-use categories. Self-hosting gives you control over data residency and model version, but you become responsible for patching, capacity, and safety filters.',
            ),
            (
                'Capacity and cost',
                'A rough VRAM estimate is parameters times bytes per parameter times an overhead factor. A 7B model at 2 bytes per parameter needs about 14 GB for weights before KV cache and runtime overhead. Quantization reduces memory but can change quality; measure it on your evaluation set rather than assuming.',
            ),
            (
                'Quality and maintenance',
                'The hosted API may hide a model upgrade that changes behaviour. A self-hosted model stays fixed until you choose to upgrade, but you must run evaluations, security patches, and capacity planning yourself. The cheapest token is not the cheapest system once GPU idle time and on-call are included.',
            ),
        ],
        [
            ('Open-weight model', 'A model whose trained parameters are published for download, often under a licence with conditions.'),
            ('Quantization', 'Reducing the precision of model weights, such as 16-bit to 8-bit, to save memory at a possible quality cost.'),
            ('VRAM', 'Memory on a GPU; model weights, KV cache, and runtime buffers must fit inside it.'),
            ('Serving stack', 'The runtime around a model, such as vLLM or TGI, that batches requests and exposes an API.'),
            ('Model licence', 'The legal terms governing use, redistribution, and acceptable use of a model.'),
        ],
        'Self-hosting an open-weight model is like running your own kitchen: you control the ingredients, but you also own the fridge, the chef rota, and the health inspection.',
        'A team wants to self-host an 8B model to avoid per-token fees. Their peak is 40 requests per second with a 2-second p95 target. The estimate shows two GPUs, not one, once KV cache and headroom are included. They compare the fully loaded GPU cost with the hosted bill, then run the same 300-case evaluation on both. The hosted model wins on quality and cost at their volume, so they keep self-hosting as a documented fallback rather than a default.',
        [
            'Read the model licence and record the restrictions that affect your product.',
            'Estimate weights, KV cache, and runtime overhead for your expected context length.',
            'Benchmark quality, p95 latency, and cost per request on a representative evaluation set.',
            'Check the serving stack for batching, quantization support, and observability.',
            'Write the upgrade, rollback, and capacity plan before production traffic reaches the endpoint.',
        ],
        _code(
            'A conservative VRAM estimate that makes assumptions explicit.',
            '''
            def vram_gb(params_b: float, bytes_per_param: float = 2.0, overhead: float = 1.25) -> float:
                if params_b <= 0 or bytes_per_param <= 0 or overhead < 1:
                    raise ValueError("invalid model sizing input")
                return round(params_b * bytes_per_param * overhead, 1)


            print(vram_gb(7, 2.0))  # weights plus a small overhead factor
            ''',
            'python',
            [
                'The estimate covers weights and a simple overhead factor, not the KV cache for long contexts or a second replica for availability.',
                'bytes_per_param is 2 for 16-bit weights and 1 for 8-bit; real quantization formats vary.',
                'A capacity plan needs measured throughput and headroom, not only a memory estimate.',
            ],
        ),
        [
            'Choosing a model because it is open-weight without reading the licence or measuring quality.',
            'Sizing a GPU from weights alone and ignoring KV cache, batching, and a second replica for failover.',
            'Treating a self-hosted endpoint as free after the GPU is rented, ignoring on-call and upgrade work.',
        ],
        [
            'Pin the model revision and record its licence, evaluation date, and serving configuration.',
            'Keep a hosted fallback and a tested rollback path; self-hosting is an operational commitment.',
            'Re-run quality and safety evaluations after any quantization, runtime, or model revision change.',
        ],
        [
            'I can distinguish open-weight from open-source and name the licence risk.',
            'I can estimate weights, KV cache, and overhead for a candidate model.',
            'I compare hosted and self-hosted options on measured quality, latency, and total cost.',
            'I know the serving stack and observability I would need to operate.',
            'I have a rollback and upgrade plan.',
        ],
        [
            'Why does publishing weights not make a model open-source?',
            'What does quantization save, and what can it cost?',
            'Why is weights-only VRAM sizing insufficient for a production plan?',
            'Which costs disappear when you self-host, and which costs appear?',
            'How would you detect a silent hosted-model upgrade?',
            'When is a hosted API the more responsible choice even at a higher token price?',
        ],
        [
            'Read one model licence and write down three restrictions that affect a commercial product (25 minutes).',
            'Estimate VRAM for a 7B, 13B, and 70B model at 16-bit and 8-bit, then explain the assumptions (25 minutes).',
            'Run the same ten evaluation cases against a hosted and a local model, and compare quality, latency, and cost (40 minutes).',
        ],
        'The capstone may use a hosted or self-hosted model, but the decision record must show licence, quality, latency, cost, and operational ownership. This lesson gives you the evidence table.',
        'Start with the hosted option unless you have a measured reason to self-host. A GPU is not a strategy.',
        [
            'Open-weight releases parameters; open-source also releases the code and data under a licence that permits the full freedom to study, change, and share.',
            'Quantization reduces memory and may improve throughput, but it can reduce accuracy or change failure modes.',
            'Long contexts need KV cache, batching needs workspace, and availability needs a second replica.',
            'Per-token fees disappear; GPU rental, utilization management, patching, and on-call appear.',
            'Pin the model version if the provider exposes one, and run a canary evaluation that detects behaviour drift.',
            'When the team lacks GPU operations capacity, or the hosted model is materially better on the measured task.',
        ],
    ),
    _lesson(
        '3.17',
        '03',
        'Reasoning models and inference-time compute',
        'Decide when to spend more tokens on deliberate reasoning, and how to measure whether it pays.',
        'Reasoning models trade latency and cost for better performance on hard tasks. Without a task-level evaluation and a budget, "think longer" becomes an expensive default that makes every request slower.',
        [
            'Explain what inference-time compute buys and where it does not help.',
            'Route easy, hard, and high-risk tasks to different effort levels.',
            'Measure accuracy, latency, and cost before raising a reasoning budget.',
        ],
        [
            (
                'What inference-time compute buys',
                'A reasoning model can generate internal tokens before answering, which helps with multi-step math, code, and planning. The gain is task-dependent and usually has diminishing returns. A simple classification or extraction task often gets no benefit and pays a large latency cost.',
            ),
            (
                'Routing and budgets',
                'Use a small fast model for easy, high-volume work and reserve reasoning for hard or high-risk cases. Set a maximum reasoning budget and a total deadline. A router should have a deterministic fallback and a way to escalate when confidence or validation fails.',
            ),
            (
                'Evaluation and safety',
                'Measure the full system: accuracy, p95 latency, cost per successful task, abstention, and harmful failure rate. Do not expose hidden chain-of-thought as a product feature; expose a concise rationale, citations, and validated outputs. Watch for overthinking on tasks that were already correct.',
            ),
        ],
        [
            ('Inference-time compute', 'Extra model computation during a request, such as generating reasoning tokens, to improve a hard answer.'),
            ('Reasoning budget', 'A cap on the tokens or effort a model may spend before producing its final answer.'),
            ('Router', 'A component that sends each request to a model or effort level based on task features and policy.'),
            ('Distillation', 'Training a smaller model to imitate the useful behaviour of a larger or more expensive model.'),
            ('Overthinking', 'Spending more compute without improving the answer, often increasing latency and cost.'),
        ],
        'Reasoning effort is a dial, not a virtue. Turn it up when the task is hard and the cost of a wrong answer is high; turn it down when speed and volume matter more.',
        'A support team adds a reasoning model to every ticket classification. Accuracy rises from 91% to 91.4%, but p95 latency triples and cost increases fivefold. They route only refund and policy exceptions to the reasoning model, keep simple labels on the small model, and add a validation fallback. The blended accuracy is 93% at a fraction of the cost.',
        [
            'Define the task and the cost of a wrong answer before choosing an effort level.',
            'Run a baseline with a small model and a fixed prompt on a representative evaluation set.',
            'Run the same set at low, medium, and high reasoning effort and record quality, latency, and cost.',
            'Choose a routing rule with a fallback for validation failures.',
            'Monitor the routed mix and re-evaluate after any model or prompt change.',
        ],
        _code(
            'A transparent effort router with a deterministic fallback.',
            '''
            def choose_effort(complexity: str, risk: str, budget: str) -> str:
                levels = {"low", "medium", "high"}
                if complexity not in levels or risk not in levels or budget not in levels:
                    raise ValueError("complexity, risk, and budget must be low, medium, or high")
                if complexity == "low" and risk == "low":
                    return "small"
                if budget == "low":
                    return "low"
                if complexity == "high" or risk == "high":
                    return "high"
                return "medium"


            print(choose_effort("high", "high", "medium"))
            ''',
            'python',
            [
                'The router returns a named policy, not a model name, so the deployment can change models without rewriting the rule.',
                'Risk can override complexity because a wrong high-impact answer is expensive even when the task looks simple.',
                'The rule is deliberately small enough to test; a learned router needs its own evaluation and fallback.',
            ],
        ),
        [
            'Sending every request to the most expensive reasoning model because it is the newest.',
            'Judging a reasoning upgrade on a handful of impressive examples instead of a representative evaluation set.',
            'Treating hidden reasoning text as a citation or a guarantee of correctness.',
        ],
        [
            'Record the reasoning budget, model version, and routing rule with every evaluation run.',
            'Cap total latency and cost per request; a reasoning model that misses the deadline is a failure even if its answer is better.',
            'Validate the final answer and keep a fallback path for refusals, invalid JSON, and timeouts.',
        ],
        [
            'I can explain what reasoning tokens buy and what they cost.',
            'I have a baseline from a smaller model before adding reasoning.',
            'I route hard or high-risk tasks rather than sending everything to the largest model.',
            'I measure accuracy, p95 latency, and cost per successful task.',
            'I have a fallback for invalid or timed-out reasoning output.',
        ],
        [
            'Why can a reasoning model improve a math answer but not a simple label extraction?',
            'What should a routing rule use besides task difficulty?',
            'Why is accuracy alone an incomplete evaluation of a reasoning upgrade?',
            'What is overthinking, and how would you detect it?',
            'Why should hidden chain-of-thought not be shown as a citation?',
            'When would distillation be a better answer than routing to a larger model?',
        ],
        [
            'Build a ten-case evaluation set with expected answers and a wrong-answer cost for each (25 minutes).',
            'Run a small model and a reasoning model on the same cases, then record accuracy, p95 latency, and cost (40 minutes).',
            'Write a routing rule for the cases and test it against the evaluation set (25 minutes).',
        ],
        'The capstone can route high-risk actions to a reasoning model, but the evaluation must show the quality gain and the latency budget. This lesson supplies the decision record.',
        'If you cannot measure the gain, do not pay for the reasoning budget. A baseline is the most valuable experiment.',
        [
            'Reasoning helps when the task needs multiple internal steps; simple extraction has little to reason about.',
            'The cost of a wrong answer, the latency budget, and the user impact.',
            'A slower, more expensive system can reduce successful throughput even when its raw accuracy rises.',
            'Spending more effort while the answer quality stays flat; compare quality per unit cost and latency.',
            'A hidden rationale is not evidence; use validated outputs, citations, and a visible explanation.',
            'When you need the quality of the larger model at the latency and cost of a smaller one, and you have enough examples to train and evaluate.',
        ],
    ),
    _lesson(
        '3.18',
        '03',
        'Fine-tuning and adaptation decisions',
        'Compare prompting, retrieval, fine-tuning, and distillation using evidence rather than novelty.',
        'Most quality problems are data, retrieval, or prompt problems. Fine-tuning is justified when you have many consistent examples, a stable task, and a measured gap that adaptation can close.',
        [
            'Choose among prompting, retrieval, fine-tuning, and distillation for a given problem.',
            'Prepare a clean training and evaluation split that does not leak answers.',
            'Plan the serving, regression testing, and rollback for an adapted model.',
        ],
        [
            (
                'Start with the cheapest intervention',
                'A clearer prompt, a better schema, and a small evaluation set often beat fine-tuning. If the model lacks fresh or private facts, use retrieval rather than training facts into weights. Fine-tuning teaches behaviour and format; it is a poor database.',
            ),
            (
                'When fine-tuning helps',
                'Fine-tuning is a good fit for a stable task with hundreds or thousands of consistent examples, a specific output style, or a smaller model that must match a larger model on a narrow task. It is a poor fit when the requirements change weekly or the data is scarce and unverified.',
            ),
            (
                'Data and evaluation',
                'Split examples into train, validation, and test sets before training. Remove duplicates and leakage. Keep the same golden set across prompt, retrieval, and fine-tuned variants so the comparison is honest. Monitor for catastrophic forgetting on unrelated tasks and keep a rollback to the base model.',
            ),
        ],
        [
            ('Fine-tuning', 'Continuing training on labelled examples to adapt a model\'s behaviour or format.'),
            ('LoRA', 'A parameter-efficient fine-tuning method that trains small adapter weights instead of the full model.'),
            ('Distillation', 'Training a smaller student model to reproduce the useful behaviour of a larger teacher.'),
            ('Catastrophic forgetting', 'Losing previously learned capabilities after training on a narrow new dataset.'),
            ('Golden set', 'A stable, representative evaluation set used to compare model and prompt variants.'),
        ],
        'Fine-tuning is a scalpel, not a first-aid kit. Use it when you can name the behaviour gap and measure the change against a stable evaluation set.',
        'A team fine-tunes a model to answer product questions, but the answers change every week. The adapted model confidently repeats last month\'s prices. They move product facts into retrieval, keep a small fine-tune for tone and JSON format, and add a citation check. Quality improves, and a price change no longer requires retraining.',
        [
            'Write the behaviour gap and the evidence that prompting and retrieval did not close it.',
            'Build a labelled dataset with a held-out test split that reflects production traffic.',
            'Try prompting and retrieval baselines on the same golden set.',
            'Fine-tune a small adapter, evaluate on the held-out set, and check unrelated tasks for regressions.',
            'Plan serving, versioning, monitoring, and rollback before exposing the model to users.',
        ],
        _code(
            'A small decision function that makes the adaptation trade-off explicit.',
            '''
            def choose_adaptation(
                examples: int,
                needs_fresh_facts: bool,
                latency_sensitive: bool,
                privacy_required: bool,
            ) -> str:
                if needs_fresh_facts:
                    return "retrieval"
                if examples < 50:
                    return "prompting"
                if latency_sensitive:
                    return "distillation"
                if privacy_required or examples >= 500:
                    return "fine_tuning"
                return "prompting"
            ''',
            'python',
            [
                'Fresh facts belong in retrieval; training them into weights makes every update a retraining project.',
                'The example threshold is a starting heuristic, not a law; the evaluation determines whether adaptation pays.',
                'Privacy can justify self-hosting or fine-tuning, but it also creates data-handling obligations.',
            ],
        ),
        [
            'Fine-tuning to add facts that change frequently instead of using retrieval.',
            'Training and testing on the same examples, then reporting an inflated score.',
            'Skipping the prompt and retrieval baselines, so the fine-tuning gain is unknown.',
        ],
        [
            'Version the training data, adapter, base model, and evaluation report together.',
            'Keep a base-model fallback and a regression suite for unrelated capabilities.',
            'Review the data for personal information, licence restrictions, and label quality before training.',
        ],
        [
            'I can explain when prompting or retrieval is the better first move.',
            'I have a held-out test set that does not leak into training.',
            'I compare fine-tuning with the same baseline used for prompts and retrieval.',
            'I check unrelated capabilities for forgetting or safety regressions.',
            'I have a serving, versioning, and rollback plan.',
        ],
        [
            'Why is fine-tuning a poor way to add facts that change every week?',
            'What makes a good fine-tuning dataset?',
            'Why does a held-out test set matter more than a high training score?',
            'When does distillation make sense?',
            'What is catastrophic forgetting, and how would you detect it?',
            'Which operational costs appear after you deploy an adapted model?',
        ],
        [
            'Write a one-page decision record comparing prompting, retrieval, and fine-tuning for your capstone (25 minutes).',
            'Create a 20-example labelled set, hold out five, and verify there is no duplicate leakage (30 minutes).',
            'Run a prompt baseline and a small fine-tune on the same test split, then record quality, latency, and cost (60 minutes).',
        ],
        'The capstone should use prompting and retrieval by default. If it fine-tunes, the decision record and held-out evaluation are the evidence that the adaptation was justified.',
        'Do not fine-tune until you can state the behaviour gap in one sentence and measure it on a held-out set.',
        [
            'Facts change and should be retrieved from a source of truth; weights are slow and expensive to update.',
            'Representative, licensed, de-duplicated examples with consistent labels and a held-out split.',
            'Training can memorise; a held-out set estimates behaviour on unseen production requests.',
            'When a smaller student can reproduce a larger teacher\'s narrow behaviour at lower latency or cost.',
            'A drop on unrelated tasks after narrow training; test a sample of prior capabilities after each adapter.',
            'Serving infrastructure, version pinning, evaluation reruns, monitoring, and a rollback path.',
        ],
    ),
    _lesson(
        '6.18',
        '06',
        'Computer-use and browser agents',
        'Let an agent operate a browser or desktop safely, with scoped actions, approvals, and recovery.',
        'Computer-use agents can click, type, and navigate real interfaces, which makes them powerful and risky. The engineering problem is not whether the model can click; it is the permission, observability, and recovery around each action.',
        [
            'Design a small action schema that can be logged, replayed, and validated.',
            'Run the agent in a sandbox with least-privilege credentials and no unnecessary secrets.',
            'Require human approval for irreversible actions and provide a recovery path.',
        ],
        [
            (
                'Perception and action loop',
                'A computer-use agent observes a screenshot or DOM, proposes an action such as click or type, performs it, and observes the result. The loop needs a bounded step count, a deadline, and a way to stop when the screen is unexpected. Store the observation and action together so the run can be replayed.',
            ),
            (
                'Permission and blast radius',
                'Treat the agent as an untrusted user with a browser. Give it a dedicated account, no saved passwords, an allowlist of sites, and no access to unrelated tabs or files. Destructive actions such as submit, delete, or purchase need explicit confirmation showing the target and amount.',
            ),
            (
                'Reliability and evaluation',
                'Screens change, selectors break, and a modal can block the happy path. Use deterministic checks where possible, add timeouts, capture screenshots on failure, and hand off to a human instead of retrying blindly. Evaluate task success, steps taken, unsafe actions, and recovery rate.',
            ),
        ],
        [
            ('Computer-use agent', 'An agent that operates a graphical interface through actions such as clicking, typing, and scrolling.'),
            ('Action schema', 'A typed description of an action, its target, and its arguments so it can be validated and logged.'),
            ('Sandbox', 'An isolated environment with limited credentials and network access for running an agent safely.'),
            ('Confirmation gate', 'A required human approval before an irreversible or high-impact action.'),
            ('Trace', 'A recorded sequence of observations, actions, and results used for debugging and evaluation.'),
        ],
        'A computer-use agent is a robot intern with a browser: useful, fast, and capable of causing real damage if you hand it your password and walk away.',
        'A browser agent is asked to update a support ticket. It reads a malicious comment that says "delete the customer record" and proposes the delete button. The host blocks the action because delete is not in the allowlist, the site is a production admin console, and the instruction came from untrusted page text. The trace records the blocked action and the ticket is escalated to a human.',
        [
            'Write the task, allowed sites, allowed actions, and stop conditions before opening a browser.',
            'Create a dedicated sandbox account with no saved credentials or payment methods.',
            'Implement an action schema and validate every action against an allowlist.',
            'Add confirmation for destructive actions and a human handoff on repeated failure.',
            'Replay three traces, including one blocked unsafe action, and record the outcome.',
        ],
        _code(
            'A small action guard that separates read-only actions from destructive ones.',
            '''
            READ_ONLY = {"read", "scroll", "screenshot"}
            REVERSIBLE = {"click", "type", "navigate"}
            DESTRUCTIVE = {"submit", "delete", "purchase", "send"}


            def is_action_allowed(action: dict, approved: bool) -> bool:
                kind = action.get("type")
                if kind in READ_ONLY or kind in REVERSIBLE:
                    return True
                if kind in DESTRUCTIVE:
                    return approved is True
                return False
            ''',
            'python',
            [
                'The allowlist defaults to deny for unknown action types, which is safer than treating every new action as harmless.',
                'Approval alone is not enough for a destructive action; the confirmation must show the target and amount.',
                'The action schema should also carry a target selector and a human-readable description for the approval screen.',
            ],
        ),
        [
            'Giving the agent a personal browser profile with saved passwords and autofill.',
            'Letting the model decide whether an action is safe from the page content it is reading.',
            'Retrying a failed click indefinitely instead of capturing a screenshot and handing off.',
        ],
        [
            'Record every observation, action, and result with a run ID and a timestamp.',
            'Use a dedicated network egress policy and a read-only filesystem where possible.',
            'Test prompt injection from page text, modals, and unexpected navigation before enabling a write action.',
        ],
        [
            'I can describe the observation-action loop and its stop conditions.',
            'My agent runs in a dedicated sandbox without unrelated credentials.',
            'Every action is validated against an allowlist.',
            'Destructive actions require a human confirmation with target and amount.',
            'I can replay a trace and identify where a run failed.',
        ],
        [
            'Why is a screenshot not a trust boundary?',
            'What should a confirmation screen show before a destructive action?',
            'Why does an allowlist beat a blocklist for agent actions?',
            'How would page text inject an instruction into the agent?',
            'What should happen after three failed attempts?',
            'Which metrics would you track for a computer-use agent?',
        ],
        [
            'Write an action schema and an allowlist for a browser task (25 minutes).',
            'Run a read-only agent in a sandbox against a test site and capture three traces (40 minutes).',
            'Add a destructive-action confirmation and test that the action is blocked without approval (30 minutes).',
        ],
        'If the capstone uses computer use, the project must show a sandbox, an action allowlist, a confirmation gate, and replayable traces. This lesson defines that evidence.',
        'Start read-only. A browser agent that can only read and screenshot is still useful and much easier to make safe.',
        [
            'A screenshot can contain attacker-controlled text and cannot establish whether an action is safe.',
            'The exact target, the amount or consequence, the source of the instruction, and the reversibility.',
            'An allowlist denies unknown actions by default; a blocklist misses new or unusual actions.',
            'The page can contain text that looks like an instruction; the agent must treat it as untrusted data.',
            'Stop, capture the trace, and hand off to a human with the failure context.',
            'Task success, steps, unsafe-action attempts, human handoffs, latency, and cost per successful task.',
        ],
    ),
    _lesson(
        '7.18',
        '07',
        'Agent-to-agent (A2A) collaboration',
        'Coordinate specialist agents with explicit capabilities, handoffs, budgets, and shared evidence.',
        'A2A protocols let agents discover and delegate to each other, but interoperability does not remove the need for contracts. Without capability checks, budget limits, and traceable handoffs, multi-agent systems become expensive telephone games.',
        [
            'Describe an agent card with capabilities, limits, and authentication requirements.',
            'Design a handoff envelope that carries evidence, open questions, and a remaining budget.',
            'Decide when a single agent or workflow is a better choice than A2A.',
        ],
        [
            (
                'Agent cards and capabilities',
                'An agent card advertises what an agent can do, how to authenticate, and what it returns. Discovery is not trust: verify the card against a registry or allowlist, and check the requested capability against the receiving agent\'s policy. A self-description from an untrusted agent is data, not permission.',
            ),
            (
                'Handoffs with evidence',
                'A handoff should carry verified facts, the reason for the transfer, open questions, the tools already tried, and the remaining token or cost budget. The receiving agent must not repeat a failed path or exceed the original budget. Keep a shared trace ID so a human can reconstruct the whole task.',
            ),
            (
                'When not to use A2A',
                'Every network hop adds latency, failure modes, and coordination cost. Use A2A when separate teams own genuinely different capabilities and a single agent cannot hold the required tools or permissions. Measure task success, total cost, and latency against a single-agent baseline before expanding.',
            ),
        ],
        [
            ('A2A', 'A protocol pattern for discovering, authenticating, and delegating tasks between agents.'),
            ('Agent card', 'A machine-readable description of an agent\'s capabilities, endpoint, and authentication requirements.'),
            ('Handoff', 'A structured transfer of a task, evidence, budget, and constraints from one agent to another.'),
            ('Capability', 'A named action or domain an agent is allowed to perform, checked by policy rather than self-description.'),
            ('Coordination cost', 'The extra latency, tokens, failure modes, and human effort introduced by splitting work across agents.'),
        ],
        'A2A is a relay race, not a group chat: each runner gets a clear baton, a lane, and a budget, and the team records where the baton was dropped.',
        'A research agent finds a contract clause but cannot sign it. It hands off to a legal agent with the clause text, the source URL, the open question, and 4,000 remaining tokens. The legal agent checks its capability card, confirms the clause is within policy, and returns a cited recommendation. The orchestrator records both traces under one task ID.',
        [
            'Define the user task and decide whether a single agent can own it end to end.',
            'Write agent cards with capabilities, authentication, limits, and output schema.',
            'Design a handoff envelope with facts, open questions, tried paths, and a remaining budget.',
            'Add a registry or allowlist and reject capabilities the receiver does not explicitly permit.',
            'Compare the multi-agent result with a single-agent baseline on success, cost, and latency.',
        ],
        _code(
            'A deterministic capability-and-budget router for a handoff.',
            '''
            def route_task(task: dict, agents: list[dict], remaining_budget: int) -> str | None:
                capability = task.get("capability")
                eligible = [
                    agent for agent in agents
                    if agent.get("healthy")
                    and capability in agent.get("capabilities", ())
                    and agent.get("cost", 0) <= remaining_budget
                ]
                if not eligible:
                    return None
                return min(eligible, key=lambda agent: (agent["cost"], agent["id"]))["id"]
            ''',
            'python',
            [
                'The router checks capability, health, and budget before choosing; a discovered agent is not automatically eligible.',
                'Ties break by ID so the same request produces the same route, which makes traces easier to compare.',
                'A real router also verifies authentication and records the rejected candidates and reasons.',
            ],
        ),
        [
            'Trusting an agent card\'s capabilities without checking the registry and local policy.',
            'Passing the whole conversation to every agent, including secrets and stale instructions.',
            'Adding agents to improve quality without a single-agent baseline or a cost budget.',
        ],
        [
            'Record one trace ID across every handoff and include the rejected routes and reasons.',
            'Enforce a total budget and deadline at the orchestrator, not only inside each agent.',
            'Version agent cards and test compatibility when a capability or schema changes.',
        ],
        [
            'I can write an agent card with capabilities and limits.',
            'I can design a handoff envelope with facts, open questions, and budget.',
            'I verify capability and authentication rather than trusting self-description.',
            'I keep one trace ID across the whole multi-agent task.',
            'I have a single-agent baseline for comparison.',
        ],
        [
            'What is the difference between discovery and trust in A2A?',
            'Which fields belong in a handoff envelope?',
            'Why can adding agents make a system less reliable?',
            'How would you prevent an agent from exceeding the total task budget?',
            'What should happen when no eligible agent has the requested capability?',
            'Which measurements would justify keeping a multi-agent design?',
        ],
        [
            'Write agent cards for two specialist agents and one orchestrator (25 minutes).',
            'Implement a handoff envelope and a router that rejects missing capabilities and over-budget agents (30 minutes).',
            'Run one task through a single agent and the multi-agent path, then compare success, cost, and latency (45 minutes).',
        ],
        'If the capstone uses A2A, the project must show agent cards, authenticated capability checks, budgeted handoffs, shared traces, and a single-agent baseline. Otherwise, keep the simpler design.',
        'A multi-agent system is a distributed system. Add it only when the evaluation shows a benefit that justifies the coordination cost.',
        [
            'Discovery finds agents; trust comes from authentication, registry allowlists, and local policy.',
            'Verified facts, reason for transfer, open questions, tried paths, remaining budget, deadline, and trace ID.',
            'Each hop adds latency, failure modes, and opportunities to lose or duplicate context.',
            'Enforce a budget and deadline at the orchestrator and pass the remaining amount in every handoff.',
            'Return a typed no-route result and escalate to a human or a fallback workflow.',
            'Task success, cost, p95 latency, handoff count, and human escalation rate against a single-agent baseline.',
        ],
    ),
]


EXERCISES = [
    {
        'id': 'python-first-script',
        'lesson_id': '0.06',
        'title': 'Format your first order total',
        'instructions': 'Implement describe_order(name, tickets, price). Return a string in the form "Ada: 37.50" using two decimal places. Reject negative tickets or price with ValueError.',
        'starter_code': dedent('''
            def describe_order(name, tickets, price):
                # TODO: validate and format the total.
                raise NotImplementedError


            print(describe_order("Ada", 3, 12.5))
        ''').strip(),
        'checks_code': dedent('''
            assert describe_order("Ada", 3, 12.5) == "Ada: 37.50"
            assert describe_order("Bo", 0, 9.99) == "Bo: 0.00"
            for args in [("X", -1, 1), ("X", 1, -1)]:
                try:
                    describe_order(*args)
                except ValueError:
                    pass
                else:
                    raise AssertionError("negative values must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def describe_order(name, tickets, price):
                if tickets < 0 or price < 0:
                    raise ValueError("tickets and price must be non-negative")
                return f"{name}: {tickets * price:.2f}"
        ''').strip(),
        'estimated_minutes': 15,
    },
    {
        'id': 'python-inventory-value',
        'lesson_id': '0.07',
        'title': 'Total a list of inventory records',
        'instructions': 'Implement inventory_value(items). Each item is a dictionary with quantity and unit_price. Return the total rounded to two decimals, return 0 for an empty list, and raise ValueError for negative or missing values.',
        'starter_code': dedent('''
            def inventory_value(items):
                # TODO: loop over the records and sum quantity * unit_price.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            records = [
                {"quantity": 2, "unit_price": 3.5},
                {"quantity": 1, "unit_price": 10.0},
            ]
            assert inventory_value(records) == 17.0
            assert inventory_value([]) == 0
            for bad in [[{"quantity": -1, "unit_price": 1}], [{"quantity": 1}]]:
                try:
                    inventory_value(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError("invalid records must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def inventory_value(items):
                total = 0.0
                for item in items:
                    try:
                        quantity = item["quantity"]
                        price = item["unit_price"]
                    except (KeyError, TypeError) as exc:
                        raise ValueError("quantity and unit_price are required") from exc
                    if quantity < 0 or price < 0:
                        raise ValueError("values must be non-negative")
                    total += quantity * price
                return round(total, 2)
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'python-safe-divide',
        'lesson_id': '0.08',
        'title': 'Write a safe division function',
        'instructions': 'Implement safe_divide(numerator, denominator, default=0.0). Return the rounded quotient, return default when the denominator is zero, and raise ValueError if either input is not a number or is a boolean.',
        'starter_code': dedent('''
            def safe_divide(numerator, denominator, default=0.0):
                # TODO: validate and divide without ZeroDivisionError.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert safe_divide(10, 4) == 2.5
            assert safe_divide(1, 0) == 0.0
            assert safe_divide(1, 0, default=None) is None
            for args in [("10", 2), (10, True)]:
                try:
                    safe_divide(*args)
                except ValueError:
                    pass
                else:
                    raise AssertionError("invalid numeric inputs must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def safe_divide(numerator, denominator, default=0.0):
                for value in (numerator, denominator):
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise ValueError("numerator and denominator must be numbers")
                if denominator == 0:
                    return default
                return round(numerator / denominator, 4)
        ''').strip(),
        'estimated_minutes': 15,
    },
    {
        'id': 'python-json-summary',
        'lesson_id': '0.09',
        'title': 'Summarise a JSON payload',
        'instructions': 'Implement summarize_payload(text). Decode JSON, require a top-level object, and return {"name": name_or_empty_string, "items": number_of_items}. Raise ValueError for invalid JSON, a non-object top level, or a non-list items field.',
        'starter_code': dedent('''
            import json


            def summarize_payload(text):
                # TODO: decode, validate, and summarise.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert summarize_payload('{"name": "demo", "items": [1, 2]}') == {"name": "demo", "items": 2}
            assert summarize_payload('{"items": []}') == {"name": "", "items": 0}
            for bad in ["{", "[]", '{"items": "nope"}']:
                try:
                    summarize_payload(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError("invalid payloads must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            import json


            def summarize_payload(text):
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid JSON") from exc
                if not isinstance(data, dict):
                    raise ValueError("expected a JSON object")
                items = data.get("items", [])
                if not isinstance(items, list):
                    raise ValueError("items must be a list")
                name = data.get("name", "")
                return {"name": name if isinstance(name, str) else "", "items": len(items)}
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'git-conventional-message',
        'lesson_id': '0.10',
        'title': 'Check a commit message',
        'instructions': 'Implement is_conventional_commit(message). Accept a message with an allowed type (feat, fix, docs, test, refactor, chore), an optional lowercase scope in parentheses, a colon and space, then a non-empty summary. Reject a trailing period and a message longer than 72 characters.',
        'starter_code': dedent('''
            import re


            def is_conventional_commit(message):
                # TODO: validate the commit message format.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert is_conventional_commit("feat(api): add retry budget") is True
            assert is_conventional_commit("fix: handle empty input") is True
            assert is_conventional_commit("update stuff") is False
            assert is_conventional_commit("feat: add thing.") is False
            assert is_conventional_commit("feat: " + "x" * 80) is False
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            import re


            PATTERN = re.compile(r"^(feat|fix|docs|test|refactor|chore)(\\([a-z0-9-]+\\))?: \\S.{0,49}$")


            def is_conventional_commit(message):
                if not isinstance(message, str) or len(message) > 72:
                    return False
                if message.rstrip().endswith("."):
                    return False
                return PATTERN.fullmatch(message.strip()) is not None
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'python-http-status',
        'lesson_id': '0.11',
        'title': 'Classify HTTP status codes',
        'instructions': 'Implement classify_status(code) returning success, redirect, client_error, server_error, or unknown. Implement retryable(code) returning True only for 429, 500, 502, 503, and 504. Reject non-integer or boolean codes with ValueError.',
        'starter_code': dedent('''
            def classify_status(code):
                # TODO: classify by the first digit.
                raise NotImplementedError


            def retryable(code):
                # TODO: return True only for transient failures.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert classify_status(200) == "success"
            assert classify_status(301) == "redirect"
            assert classify_status(404) == "client_error"
            assert classify_status(503) == "server_error"
            assert classify_status(99) == "unknown"
            assert retryable(429) is True
            assert retryable(503) is True
            assert retryable(422) is False
            for bad in ["200", True]:
                try:
                    classify_status(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError("invalid codes must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def _validate(code):
                if isinstance(code, bool) or not isinstance(code, int):
                    raise ValueError("status code must be an integer")
                return code


            def classify_status(code):
                code = _validate(code)
                if 200 <= code <= 299:
                    return "success"
                if 300 <= code <= 399:
                    return "redirect"
                if 400 <= code <= 499:
                    return "client_error"
                if 500 <= code <= 599:
                    return "server_error"
                return "unknown"


            def retryable(code):
                return _validate(code) in {429, 500, 502, 503, 504}
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'open-weight-vram',
        'lesson_id': '3.16',
        'title': 'Estimate model VRAM',
        'instructions': 'Implement estimate_vram_gb(params_b, bytes_per_param=2.0, overhead=1.2). Return the estimate rounded to one decimal place. Reject non-positive values and an overhead below 1 with ValueError.',
        'starter_code': dedent('''
            def estimate_vram_gb(params_b, bytes_per_param=2.0, overhead=1.2):
                # TODO: estimate weights plus overhead.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert estimate_vram_gb(7) == 16.8
            assert estimate_vram_gb(7, 1.0, 1.0) == 7.0
            for args in [(0,), (7, 0), (7, 2, 0.5)]:
                try:
                    estimate_vram_gb(*args)
                except ValueError:
                    pass
                else:
                    raise AssertionError("invalid sizing inputs must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def estimate_vram_gb(params_b, bytes_per_param=2.0, overhead=1.2):
                if params_b <= 0 or bytes_per_param <= 0 or overhead < 1:
                    raise ValueError("invalid model sizing input")
                return round(params_b * bytes_per_param * overhead, 1)
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'reasoning-effort-router',
        'lesson_id': '3.17',
        'title': 'Route a task to a reasoning effort',
        'instructions': 'Implement choose_effort(complexity, risk, budget). Inputs are low, medium, or high. Return small when complexity and risk are low; return low when the budget is low; return high when complexity or risk is high; otherwise return medium. Reject unknown levels with ValueError.',
        'starter_code': dedent('''
            def choose_effort(complexity, risk, budget):
                # TODO: apply the routing rules.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert choose_effort("low", "low", "high") == "small"
            assert choose_effort("medium", "medium", "low") == "low"
            assert choose_effort("high", "low", "high") == "high"
            assert choose_effort("medium", "medium", "medium") == "medium"
            try:
                choose_effort("huge", "low", "high")
            except ValueError:
                pass
            else:
                raise AssertionError("unknown levels must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def choose_effort(complexity, risk, budget):
                levels = {"low", "medium", "high"}
                if complexity not in levels or risk not in levels or budget not in levels:
                    raise ValueError("levels must be low, medium, or high")
                if complexity == "low" and risk == "low":
                    return "small"
                if budget == "low":
                    return "low"
                if complexity == "high" or risk == "high":
                    return "high"
                return "medium"
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'adaptation-decision',
        'lesson_id': '3.18',
        'title': 'Choose an adaptation strategy',
        'instructions': 'Implement choose_adaptation(examples, needs_fresh_facts, latency_sensitive, privacy_required). Return retrieval for fresh facts, prompting below 50 examples, distillation when latency matters, fine_tuning when privacy is required or there are at least 500 examples, otherwise prompting. Reject a negative example count.',
        'starter_code': dedent('''
            def choose_adaptation(examples, needs_fresh_facts, latency_sensitive, privacy_required):
                # TODO: choose the simplest method that fits the constraints.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert choose_adaptation(1000, True, False, False) == "retrieval"
            assert choose_adaptation(10, False, False, False) == "prompting"
            assert choose_adaptation(100, False, True, False) == "distillation"
            assert choose_adaptation(100, False, False, True) == "fine_tuning"
            assert choose_adaptation(600, False, False, False) == "fine_tuning"
            try:
                choose_adaptation(-1, False, False, False)
            except ValueError:
                pass
            else:
                raise AssertionError("negative example counts must be rejected")
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def choose_adaptation(examples, needs_fresh_facts, latency_sensitive, privacy_required):
                if examples < 0:
                    raise ValueError("examples must be non-negative")
                if needs_fresh_facts:
                    return "retrieval"
                if examples < 50:
                    return "prompting"
                if latency_sensitive:
                    return "distillation"
                if privacy_required or examples >= 500:
                    return "fine_tuning"
                return "prompting"
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'computer-use-action-guard',
        'lesson_id': '6.18',
        'title': 'Guard computer-use actions',
        'instructions': 'Implement is_action_allowed(action, approved). read, scroll, and screenshot are always allowed; click, type, and navigate are allowed; submit, delete, purchase, and send require approved=True; unknown action types are denied.',
        'starter_code': dedent('''
            def is_action_allowed(action, approved):
                # TODO: allow read-only actions and gate destructive ones.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            assert is_action_allowed({"type": "read"}, False) is True
            assert is_action_allowed({"type": "click"}, False) is True
            assert is_action_allowed({"type": "delete"}, False) is False
            assert is_action_allowed({"type": "delete"}, True) is True
            assert is_action_allowed({"type": "unknown"}, True) is False
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            READ_ONLY = {"read", "scroll", "screenshot"}
            REVERSIBLE = {"click", "type", "navigate"}
            DESTRUCTIVE = {"submit", "delete", "purchase", "send"}


            def is_action_allowed(action, approved):
                kind = action.get("type") if isinstance(action, dict) else None
                if kind in READ_ONLY or kind in REVERSIBLE:
                    return True
                if kind in DESTRUCTIVE:
                    return approved is True
                return False
        ''').strip(),
        'estimated_minutes': 20,
    },
    {
        'id': 'a2a-capability-router',
        'lesson_id': '7.18',
        'title': 'Route an A2A handoff',
        'instructions': 'Implement route_task(task, agents, remaining_budget). A task has a capability. Eligible agents are healthy, advertise the capability, and have cost <= remaining_budget. Return the cheapest eligible agent id, breaking ties by id, or None.',
        'starter_code': dedent('''
            def route_task(task, agents, remaining_budget):
                # TODO: filter and choose deterministically.
                raise NotImplementedError
        ''').strip(),
        'checks_code': dedent('''
            agents = [
                {"id": "legal-b", "capabilities": ["legal"], "healthy": True, "cost": 3},
                {"id": "legal-a", "capabilities": ["legal"], "healthy": True, "cost": 3},
                {"id": "legal-c", "capabilities": ["legal"], "healthy": False, "cost": 1},
                {"id": "research", "capabilities": ["research"], "healthy": True, "cost": 1},
            ]
            assert route_task({"capability": "legal"}, agents, 5) == "legal-a"
            assert route_task({"capability": "legal"}, agents, 2) is None
            assert route_task({"capability": "unknown"}, agents, 100) is None
            print("All checks passed.")
        ''').strip(),
        'solution_code': dedent('''
            def route_task(task, agents, remaining_budget):
                capability = task.get("capability") if isinstance(task, dict) else None
                eligible = [
                    agent for agent in agents
                    if agent.get("healthy")
                    and capability in agent.get("capabilities", ())
                    and agent.get("cost", 0) <= remaining_budget
                ]
                if not eligible:
                    return None
                return min(eligible, key=lambda agent: (agent["cost"], agent["id"]))["id"]
        ''').strip(),
        'estimated_minutes': 25,
    },
]


RESOURCES = {
    '0.06': {'article': {'title': 'Python Tutorial: An Informal Introduction', 'url': 'https://docs.python.org/3/tutorial/introduction.html'}},
    '0.07': {'article': {'title': 'Python Tutorial: Data Structures', 'url': 'https://docs.python.org/3/tutorial/datastructures.html'}},
    '0.08': {'article': {'title': 'Python Tutorial: Defining Functions', 'url': 'https://docs.python.org/3/tutorial/controlflow.html#defining-functions'}},
    '0.09': {'article': {'title': 'Python json documentation', 'url': 'https://docs.python.org/3/library/json.html'}},
    '0.10': {'article': {'title': 'Pro Git, second edition', 'url': 'https://git-scm.com/book/en/v2'}},
    '0.11': {'article': {'title': 'MDN: Overview of HTTP', 'url': 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview'}},
    '3.16': {'article': {'title': 'Hugging Face Transformers documentation', 'url': 'https://huggingface.co/docs/transformers/index'}},
    '3.17': {'article': {'title': 'OpenAI reasoning guide', 'url': 'https://platform.openai.com/docs/guides/reasoning'}},
    '3.18': {'article': {'title': 'Hugging Face PEFT documentation', 'url': 'https://huggingface.co/docs/peft/index'}},
    '6.18': {'article': {'title': 'Anthropic computer use documentation', 'url': 'https://docs.anthropic.com/en/docs/build-with-claude/computer-use'}},
    '7.18': {'article': {'title': 'Agent2Agent (A2A) protocol', 'url': 'https://a2a-protocol.org/'}},
}


MODULE_RESOURCES = {
    '00': {'article': {'title': 'Python for Beginners', 'url': 'https://www.python.org/about/gettingstarted/'}},
    '01': {'article': {'title': 'Official Python Tutorial', 'url': 'https://docs.python.org/3/tutorial/index.html'}},
    '02': {'article': {'title': 'FastAPI documentation', 'url': 'https://fastapi.tiangolo.com/'}},
    '03': {'article': {'title': 'OpenAI text generation guide', 'url': 'https://platform.openai.com/docs/guides/text-generation'}},
    '04': {'article': {'title': 'OpenAI prompt engineering guide', 'url': 'https://platform.openai.com/docs/guides/prompt-engineering'}},
    '05': {'article': {'title': 'Retrieval-augmented generation overview', 'url': 'https://www.pinecone.io/learn/retrieval-augmented-generation/'}},
    '06': {'article': {'title': 'OpenAI agents guide', 'url': 'https://platform.openai.com/docs/guides/agents'}},
    '07': {'article': {'title': 'Agent2Agent protocol', 'url': 'https://a2a-protocol.org/'}},
    '08': {'article': {'title': 'Model Context Protocol specification', 'url': 'https://modelcontextprotocol.io/'}},
    '09': {'article': {'title': 'OpenTelemetry documentation', 'url': 'https://opentelemetry.io/docs/'}},
    '10': {'article': {'title': 'Docker getting started', 'url': 'https://docs.docker.com/get-started/'}},
    '11': {'article': {'title': 'AWS Well-Architected Framework', 'url': 'https://aws.amazon.com/architecture/well-architected/'}},
    '12': {'article': {'title': 'OpenAI production best practices', 'url': 'https://platform.openai.com/docs/guides/production-best-practices'}},
}


MAINTENANCE = {
    '3.16': ['https://huggingface.co/docs/transformers/index', 'https://docs.vllm.ai/'],
    '3.17': ['https://platform.openai.com/docs/guides/reasoning'],
    '3.18': ['https://huggingface.co/docs/peft/index', 'https://platform.openai.com/docs/guides/fine-tuning'],
    '6.18': ['https://docs.anthropic.com/en/docs/build-with-claude/computer-use'],
    '7.18': ['https://a2a-protocol.org/'],
}


PLACEMENT = {
    'title': 'Experienced learner placement check',
    'description': 'Answer ten questions about the Module 0 and early Module 1 foundations. A score of 8 or more marks those lessons as placed out. Module projects and later lessons are still required.',
    'passing_score': 8,
    'skippable_lessons': [
        '0.01', '0.02', '0.03', '0.04', '0.05',
        '0.06', '0.07', '0.08', '0.09', '0.10', '0.11',
        '1.01', '1.02', '1.03', '1.04',
    ],
    'questions': [
        {
            'id': 'q1',
            'prompt': 'Which Python value is a dictionary?',
            'options': ['[1, 2, 3]', '{"name": "Ada"}', '("a", "b")', '"a,b"'],
            'answer': 1,
        },
        {
            'id': 'q2',
            'prompt': 'What does an f-string do?',
            'options': ['Formats a file', 'Inserts expressions into a string', 'Creates a virtual environment', 'Starts a web server'],
            'answer': 1,
        },
        {
            'id': 'q3',
            'prompt': 'Which exception is raised when a dictionary key is missing?',
            'options': ['TypeError', 'KeyError', 'ValueError', 'NameError'],
            'answer': 1,
        },
        {
            'id': 'q4',
            'prompt': 'What is the main purpose of a virtual environment?',
            'options': ['Speed up the CPU', 'Isolate a project’s Python packages', 'Compress source files', 'Replace Git'],
            'answer': 1,
        },
        {
            'id': 'q5',
            'prompt': 'Which Git command records staged changes?',
            'options': ['git push', 'git commit', 'git clone', 'git status'],
            'answer': 1,
        },
        {
            'id': 'q6',
            'prompt': 'Which file should normally be excluded from Git?',
            'options': ['README.md', '.env', 'pyproject.toml', 'tests/test_app.py'],
            'answer': 1,
        },
        {
            'id': 'q7',
            'prompt': 'What does HTTP status 404 mean?',
            'options': ['Server error', 'Unauthorized', 'Resource not found', 'Success'],
            'answer': 2,
        },
        {
            'id': 'q8',
            'prompt': 'Which status codes are usually safe to retry?',
            'options': ['400 and 401', '429 and 503', '404 and 422', '200 and 201'],
            'answer': 1,
        },
        {
            'id': 'q9',
            'prompt': 'What does a function return statement do?',
            'options': ['Prints a value', 'Hands a value back to the caller', 'Creates a file', 'Starts a loop'],
            'answer': 1,
        },
        {
            'id': 'q10',
            'prompt': 'Why add type hints to a function?',
            'options': ['They enforce runtime validation automatically', 'They document intended types and help tools', 'They make Python compile faster', 'They replace tests'],
            'answer': 1,
        },
    ],
}
