#!/usr/bin/env python3
"""Disable email verification; enable simple email+password registration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ENV_FILE = Path('/opt/bedolaga/.env')


def upsert_env(key: str, value: str) -> None:
    text = ENV_FILE.read_text(encoding='utf-8') if ENV_FILE.exists() else ''
    line = f'{key}={value}'
    if f'{key}=' in text:
        out = []
        for row in text.splitlines():
            out.append(line if row.startswith(f'{key}=') else row)
        ENV_FILE.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')
    else:
        with ENV_FILE.open('a', encoding='utf-8') as f:
            f.write(line + '\n')


def psql(sql: str) -> None:
    subprocess.check_call(
        [
            'docker',
            'exec',
            'bedolaga-db',
            'psql',
            '-U',
            'postgres',
            '-d',
            'bedolaga',
            '-v',
            'ON_ERROR_STOP=1',
            '-c',
            sql,
        ]
    )


def main() -> int:
    upsert_env('CABINET_EMAIL_AUTH_ENABLED', 'true')
    upsert_env('CABINET_EMAIL_VERIFICATION_ENABLED', 'false')

    psql(
        """
        UPDATE users
        SET email_verified = true,
            email_verified_at = COALESCE(email_verified_at, NOW())
        WHERE email IS NOT NULL
          AND email != ''
          AND (email_verified IS NULL OR email_verified = false);
        """
    )

    print('Cabinet auth updated')
    print('  CABINET_EMAIL_VERIFICATION_ENABLED=false')
    return 0


if __name__ == '__main__':
    sys.exit(main())
