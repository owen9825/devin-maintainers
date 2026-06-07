# Workers

## Overview

`peon1.py` is a worker script managed by **Devin**, an AI software engineering agent that wraps Claude. It authenticates with the Devin API, creates a session delegating a task to Devin, and polls until the session completes.

## Code Style

- Python 3, no external frameworks beyond `requests`
- Credentials sourced exclusively from environment variables (`DEVIN_API_KEY`, `DEVIN_ORG_ID`, `SELF_USER_ID`)
- Flat, procedural scripts — no classes unless complexity warrants it

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
