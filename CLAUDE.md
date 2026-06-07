# Workers

## Overview

Workers are managed by **Devin**, an AI software engineering agent that wraps Claude. `task_master.py` dequeues tasks from Redis and dispatches them to `task_worker.py`, which opens Devin sessions to carry out the work and review pull requests.

## Code Style

- Python 3, no external frameworks beyond `requests`
- Credentials sourced exclusively from environment variables (`DEVIN_API_KEY`, `DEVIN_ORG_ID`, `SELF_USER_ID`)
- Flat, procedural scripts — no classes unless complexity warrants it

## CLI arguments

Always use named arguments (`--flag`) rather than positional arguments in argparse. Mark required ones with `required=True`.

```python
# Good
parser.add_argument("--title", required=True)
parser.add_argument("--notes")

# Bad
parser.add_argument("title")
```

## Module structure

Every script must be importable without side effects. All logic goes inside named functions. A bare `if __name__ == "__main__"` block at the bottom is the only place that calls those functions.

```python
# Good
def run():
    ...

if __name__ == "__main__":
    run()
```

```python
# Bad — executes on import, can't be reused
while True:
    ...
```

This applies to every `.py` file in the repo, including those in subdirectories.
