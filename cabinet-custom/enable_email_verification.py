#!/usr/bin/env python3
"""Enable cabinet email verification, Gmail SMTP relay, and Satka email templates."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path('/opt/bedolaga/.env')
ROOT = Path(__file__).resolve().parent

TEMPLATES = {
    'ru': {
        'subject': 'Подтвердите email — Satka VPN',
        'body': """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Подтверждение email</title>
</head>
<body style="margin:0;padding:0;background:#030303;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#030303;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:linear-gradient(160deg,#111111 0%,#050505 100%);border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,0.45);">
          <tr>
            <td style="padding:28px 28px 12px;text-align:center;">
              <div style="display:inline-block;width:56px;height:56px;border-radius:16px;background:linear-gradient(145deg,#34d399,#059669);color:#022c22;font-size:28px;line-height:56px;font-weight:800;">S</div>
              <h1 style="margin:18px 0 8px;color:#ffffff;font-size:24px;line-height:1.3;">Подтвердите email</h1>
              <p style="margin:0;color:#9ca3af;font-size:15px;line-height:1.6;">Спасибо за регистрацию в Satka VPN. Нажмите кнопку ниже, чтобы подтвердить адрес.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 28px 24px;text-align:center;">
              <a href="{verification_url}" style="display:inline-block;padding:14px 28px;border-radius:14px;background:linear-gradient(180deg,#6ee7b7 0%,#34d399 100%);color:#022c22;text-decoration:none;font-size:16px;font-weight:700;box-shadow:0 10px 30px rgba(16,185,129,0.28);">Подтвердить email</a>
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 24px;">
              <div style="padding:16px 18px;border-radius:14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);">
                <p style="margin:0 0 10px;color:#d1d5db;font-size:14px;line-height:1.6;">Если кнопка не работает, скопируйте ссылку:</p>
                <p style="margin:0;word-break:break-all;"><a href="{verification_url}" style="color:#6ee7b7;font-size:13px;text-decoration:none;">{verification_url}</a></p>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 28px;">
              <p style="margin:0 0 8px;color:#9ca3af;font-size:13px;line-height:1.6;">Ссылка действует {expire_hours} ч. Если вы не регистрировались — просто игнорируйте письмо.</p>
              <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.6;">{service_name} · {cabinet_url}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>""",
    },
    'en': {
        'subject': 'Verify your email — Satka VPN',
        'body': """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Verify email</title>
</head>
<body style="margin:0;padding:0;background:#030303;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#030303;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:linear-gradient(160deg,#111111 0%,#050505 100%);border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,0.45);">
          <tr>
            <td style="padding:28px 28px 12px;text-align:center;">
              <div style="display:inline-block;width:56px;height:56px;border-radius:16px;background:linear-gradient(145deg,#34d399,#059669);color:#022c22;font-size:28px;line-height:56px;font-weight:800;">S</div>
              <h1 style="margin:18px 0 8px;color:#ffffff;font-size:24px;line-height:1.3;">Verify your email</h1>
              <p style="margin:0;color:#9ca3af;font-size:15px;line-height:1.6;">Thanks for signing up for Satka VPN. Tap the button below to confirm your address.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 28px 24px;text-align:center;">
              <a href="{verification_url}" style="display:inline-block;padding:14px 28px;border-radius:14px;background:linear-gradient(180deg,#6ee7b7 0%,#34d399 100%);color:#022c22;text-decoration:none;font-size:16px;font-weight:700;box-shadow:0 10px 30px rgba(16,185,129,0.28);">Verify email</a>
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 24px;">
              <div style="padding:16px 18px;border-radius:14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);">
                <p style="margin:0 0 10px;color:#d1d5db;font-size:14px;line-height:1.6;">If the button does not work, copy this link:</p>
                <p style="margin:0;word-break:break-all;"><a href="{verification_url}" style="color:#6ee7b7;font-size:13px;text-decoration:none;">{verification_url}</a></p>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 28px;">
              <p style="margin:0 0 8px;color:#9ca3af;font-size:13px;line-height:1.6;">This link expires in {expire_hours} hours. If you did not sign up, you can ignore this email.</p>
              <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.6;">{service_name} · {cabinet_url}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>""",
    },
}


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


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upsert_template(language: str) -> None:
    tpl = TEMPLATES[language]
    psql(
        f"""
        INSERT INTO email_templates (notification_type, language, subject, body_html, is_active)
        VALUES ('email_verification', {sql_literal(language)}, {sql_literal(tpl['subject'])}, {sql_literal(tpl['body'])}, true)
        ON CONFLICT (notification_type, language)
        DO UPDATE SET
          subject = EXCLUDED.subject,
          body_html = EXCLUDED.body_html,
          is_active = true,
          updated_at = NOW();
        """
    )


def configure_env() -> None:
    upsert_env('CABINET_EMAIL_AUTH_ENABLED', 'true')
    upsert_env('CABINET_EMAIL_VERIFICATION_ENABLED', 'true')
    upsert_env('CABINET_URL', 'https://node.satkaconnect.xyz')
    upsert_env('SMTP_HOST', 'satka_postfix')
    upsert_env('SMTP_PORT', '587')
    upsert_env('SMTP_USER', '')
    upsert_env('SMTP_PASSWORD', '')
    upsert_env('SMTP_FROM_EMAIL', 'satkavpn@gmail.com')
    upsert_env('SMTP_FROM_NAME', 'Satka VPN')
    upsert_env('SMTP_USE_TLS', 'false')
    upsert_env('SMTP_USE_SSL', 'false')


def write_gmail_env(password: str) -> Path:
    env_path = ROOT / '.gmail-relay.env'
    env_path.write_text(f'GMAIL_APP_PASSWORD={password}\n', encoding='utf-8')
    env_path.chmod(0o600)
    return env_path


def restart_services(env_path: Path) -> None:
    subprocess.check_call(
        ['docker', 'compose', '-f', str(ROOT / 'postfix-compose.yml'), '--env-file', str(env_path), 'up', '-d', '--force-recreate'],
        cwd=str(ROOT),
    )
    subprocess.check_call(['docker', 'compose', 'up', '-d', 'bot', '--force-recreate'], cwd='/opt/bedolaga')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--gmail-password', default=os.environ.get('GMAIL_APP_PASSWORD'))
    args = parser.parse_args()
    if not args.gmail_password:
        print('Set --gmail-password or GMAIL_APP_PASSWORD', file=sys.stderr)
        return 1

    configure_env()
    write_gmail_env(args.gmail_password)
    upsert_template('ru')
    upsert_template('en')
    restart_services(ROOT / '.gmail-relay.env')
    print('Email verification enabled with Satka templates')
    return 0


if __name__ == '__main__':
    sys.exit(main())
