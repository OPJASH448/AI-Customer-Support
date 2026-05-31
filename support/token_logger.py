"""
Token Usage Logger

Logs every Gemini API call with token counts to a persistent file.
File location: <project_root>/logs/token_usage.jsonl

Each line is a JSON object with:
  - timestamp, user_id, username, conversation_id
  - user_message (truncated to 200 chars)
  - prompt_tokens, completion_tokens, total_tokens
"""
import os
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings

# Log file path
LOGS_DIR = Path(settings.BASE_DIR) / 'logs'
TOKEN_LOG_FILE = LOGS_DIR / 'token_usage.jsonl'


def _ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_token_usage(
    user_id: int,
    username: str,
    conversation_id: int,
    user_message: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    """
    Append a token usage record to the JSONL log file.
    Thread-safe via file append mode.
    """
    _ensure_log_dir()

    record = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'user_id': user_id,
        'username': username,
        'conversation_id': conversation_id,
        'user_message': user_message[:200],
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
    }

    with open(TOKEN_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')


def get_token_summary() -> dict:
    """
    Read the token log and return aggregate statistics.
    Returns dict with total_requests, total_tokens, by_user breakdown.
    """
    if not TOKEN_LOG_FILE.exists():
        return {'total_requests': 0, 'total_tokens': 0, 'records': []}

    records = []
    total_tokens = 0
    with open(TOKEN_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                record = json.loads(line)
                records.append(record)
                total_tokens += record.get('total_tokens', 0)

    return {
        'total_requests': len(records),
        'total_tokens': total_tokens,
        'records': records,
    }
