#!/usr/bin/env python3
"""Deploy Satka Support AI bot to remote server via SSH."""

from __future__ import annotations

import argparse
import os
import sys
import tarfile
import tempfile
from pathlib import Path

try:
    import paramiko
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "paramiko"])
    import paramiko

ROOT = Path(__file__).resolve().parent
REMOTE_DIR = "/opt/satka-support-ai"


def pack_source(tmp_path: Path) -> Path:
    archive = tmp_path / "satka-support-ai.tar.gz"
    files = [
        "auth_session.py",
        "userbot.py",
        "canned_responses.py",
        "knowledge_base.py",
        "config.py",
        "llm_client.py",
        "message_filters.py",
        "prompts.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".env.example",
        "reply_utils.py",
        "slang_style.py",
        "slang_lexicon.py",
        "troll_replies.py",
        "banter_replies.py",
        "routing.py",
    ]
    with tarfile.open(archive, "w:gz") as tar:
        for name in files:
            tar.add(ROOT / name, arcname=f"satka-support-ai/{name}")
    return archive


def run_remote(ssh: paramiko.SSHClient, cmd: str) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    return code, stdout.read().decode(), stderr.read().decode()


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy Satka Support AI")
    parser.add_argument("--host", default=os.environ.get("DEPLOY_HOST", "13.143.130.10"))
    parser.add_argument("--user", default=os.environ.get("DEPLOY_USER", "root"))
    parser.add_argument("--password", default=os.environ.get("DEPLOY_PASSWORD", ""))
    parser.add_argument("--env-file", default=os.environ.get("ENV_FILE", ""), help="Local .env to upload")
    parser.add_argument("--llm-key", default=os.environ.get("LLM_API_KEY", ""), help="Update LLM_API_KEY on server")
    parser.add_argument("--llm-model", default=os.environ.get("LLM_MODEL", ""), help="Update LLM_MODEL on server")
    parser.add_argument("--llm-base-url", default=os.environ.get("LLM_BASE_URL", ""), help="Update LLM_BASE_URL on server")
    args = parser.parse_args()

    if not args.password:
        print("Set DEPLOY_PASSWORD or --password", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        archive = pack_source(Path(tmp))
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(args.host, username=args.user, password=args.password, timeout=20)

        sftp = client.open_sftp()
        remote_archive = "/tmp/satka-support-ai.tar.gz"
        sftp.put(str(archive), remote_archive)
        sftp.close()

        cmds = [
            f"mkdir -p {REMOTE_DIR}",
            f"tar -xzf {remote_archive} -C /opt",
            f"cp -n {REMOTE_DIR}/.env.example {REMOTE_DIR}/.env || true",
        ]
        for c in cmds:
            code, out, err = run_remote(client, c)
            if code != 0:
                print(err or out, file=sys.stderr)
                return code

        if args.env_file and Path(args.env_file).is_file():
            sftp = client.open_sftp()
            sftp.put(args.env_file, f"{REMOTE_DIR}/.env")
            sftp.close()
            print("Uploaded .env")
        elif args.llm_key:
            escaped = args.llm_key.replace("'", "'\\''")
            run_remote(
                client,
                f"test -f {REMOTE_DIR}/.env || cp {REMOTE_DIR}/.env.example {REMOTE_DIR}/.env; "
                f"grep -q '^LLM_API_KEY=' {REMOTE_DIR}/.env && "
                f"sed -i 's|^LLM_API_KEY=.*|LLM_API_KEY={escaped}|' {REMOTE_DIR}/.env || "
                f"echo 'LLM_API_KEY={escaped}' >> {REMOTE_DIR}/.env",
            )
            print("Updated LLM_API_KEY on server")

        if args.llm_model:
            model = args.llm_model.replace("'", "'\\''")
            run_remote(
                client,
                f"test -f {REMOTE_DIR}/.env || cp {REMOTE_DIR}/.env.example {REMOTE_DIR}/.env; "
                f"grep -q '^LLM_MODEL=' {REMOTE_DIR}/.env && "
                f"sed -i 's|^LLM_MODEL=.*|LLM_MODEL={model}|' {REMOTE_DIR}/.env || "
                f"echo 'LLM_MODEL={model}' >> {REMOTE_DIR}/.env",
            )
            print("Updated LLM_MODEL on server")

        if args.llm_base_url:
            url = args.llm_base_url.replace("'", "'\\''")
            run_remote(
                client,
                f"test -f {REMOTE_DIR}/.env || cp {REMOTE_DIR}/.env.example {REMOTE_DIR}/.env; "
                f"grep -q '^LLM_BASE_URL=' {REMOTE_DIR}/.env && "
                f"sed -i 's|^LLM_BASE_URL=.*|LLM_BASE_URL={url}|' {REMOTE_DIR}/.env || "
                f"echo 'LLM_BASE_URL={url}' >> {REMOTE_DIR}/.env",
            )
            print("Updated LLM_BASE_URL on server")

        code, out, err = run_remote(
            client,
            f"cd {REMOTE_DIR} && docker compose build --pull && docker compose up -d --force-recreate",
        )
        print(out)
        if err:
            print(err, file=sys.stderr)
        client.close()
        return code


if __name__ == "__main__":
    raise SystemExit(main())
