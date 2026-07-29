#!/usr/bin/env python3
"""Deploy cabinet-custom files to SatkaVPN production server."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print('Install paramiko: pip install paramiko', file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parent
REMOTE_DIR = '/opt/bedolaga/cabinet-custom'
COMPOSE_CMD = 'cd /opt/bedolaga && docker compose -f cabinet-compose.yml up -d cabinet-frontend --force-recreate'

SKIP = {'deploy_cabinet.py', '__pycache__'}


def connect(host: str, user: str, password: str | None, key_path: str | None) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs: dict = {'hostname': host, 'username': user, 'timeout': 20, 'banner_timeout': 20, 'auth_timeout': 20}
    if key_path:
        kwargs['key_filename'] = key_path
    if password:
        kwargs['password'] = password
    client.connect(**kwargs)
    return client


def upload_files(client: paramiko.SSHClient) -> None:
    sftp = client.open_sftp()
    try:
        try:
            sftp.stat(REMOTE_DIR)
        except OSError:
            client.exec_command(f'mkdir -p {REMOTE_DIR}')
        for path in sorted(ROOT.iterdir()):
            if not path.is_file() or path.name in SKIP:
                continue
            remote = f'{REMOTE_DIR}/{path.name}'
            sftp.put(str(path), remote)
            print(f'uploaded {path.name}')
    finally:
        sftp.close()


def run(client: paramiko.SSHClient, cmd: str) -> None:
    print(f'$ {cmd}')
    _, stdout, stderr = client.exec_command(cmd, timeout=180)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip(), file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description='Deploy cabinet-custom to production')
    parser.add_argument('--host', default=os.environ.get('SATKA_DEPLOY_HOST', '13.143.130.10'))
    parser.add_argument('--user', default=os.environ.get('SATKA_DEPLOY_USER', 'root'))
    parser.add_argument('--password', default=os.environ.get('SATKA_DEPLOY_PASSWORD'))
    parser.add_argument('--key', default=os.environ.get('SATKA_DEPLOY_KEY'))
    args = parser.parse_args()

    if not args.password and not args.key:
        print('Set SATKA_DEPLOY_PASSWORD or SATKA_DEPLOY_KEY (or pass --password / --key)', file=sys.stderr)
        return 1

    client = connect(args.host, args.user, args.password, args.key)
    try:
        compose_src = ROOT / 'cabinet-compose.yml'
        if compose_src.exists():
            sftp = client.open_sftp()
            sftp.put(str(compose_src), '/opt/bedolaga/cabinet-compose.yml')
            sftp.close()
            print('uploaded cabinet-compose.yml')
        upload_files(client)
        run(client, COMPOSE_CMD)
        run(client, 'grep -o "satka-login-fix[^\\"]*" /opt/bedolaga/cabinet-custom/index.html | head -1')
    finally:
        client.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
