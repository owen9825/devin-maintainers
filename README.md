# Workers

An automated pipeline that monitors GitHub issues and security vulnerabilities, delegates work to [Devin](https://devin.ai) (an AI software engineering agent), and reviews the resulting pull requests against [owen9825/superset](https://github.com/owen9825/superset).

## Prerequisites

- Docker
- Python 3.12+
- A [Devin](https://devin.ai) account and API key
- A GitHub personal access token (for issue monitoring)
- Optionally, an [NVD API key](https://nvd.nist.gov/developers/request-an-api-key) (raises rate limit from 5 to 50 req/30s)

## Setup

1. Copy `sample.env` to `.env` and fill in your credentials:

```bash
cp sample.env .env
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

### 1. Start Redis

```bash
./start_containers.sh
```

### 2. Start the listeners (each in its own terminal)

The listeners monitor for new work and enqueue tasks.

```bash
# GitHub issues on apache/superset
python -m listeners.issue_listener

# CVEs from the NVD (National Vulnerability Database)
python -m listeners.nvd_listener

# CVEs from CVE MITRE
python -m listeners.cve_mitre_listener
```

### 3. Start the task master

The task master dequeues tasks and dispatches them to Devin via `task_worker.py`.

```bash
python task_master.py
```

## Utilities

Manually enqueue a task:

```bash
python create_task.py "Fix login redirect bug" task_worker --notes "Affects Safari only"
```

Check the current queue:

```bash
python queue_observer.py
```
