#!/usr/bin/env python3
"""Fix Telegram bot: one Mini App «Кабинет» button, remove legacy URL cabinet."""

from __future__ import annotations

import subprocess
import sys


def run_sql(sql: str) -> None:
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


def main() -> None:
    run_sql(
        """
        DELETE FROM main_menu_buttons
        WHERE action_type = 'url'
          AND action_value ILIKE '%satkaconnect.xyz%';

        INSERT INTO main_menu_buttons (text, action_type, action_value, visibility, is_active, display_order)
        SELECT '📱 Кабинет', 'mini_app', 'https://node.satkaconnect.xyz/', 'all', true, 0
        WHERE NOT EXISTS (
          SELECT 1 FROM main_menu_buttons
          WHERE action_type = 'mini_app'
            AND action_value ILIKE '%node.satkaconnect.xyz%'
        );

        UPDATE main_menu_buttons
        SET text = '📱 Кабинет',
            action_type = 'mini_app',
            action_value = 'https://node.satkaconnect.xyz/',
            is_active = true,
            display_order = 0
        WHERE action_type = 'mini_app'
          AND action_value ILIKE '%node.satkaconnect.xyz%';

        DELETE FROM main_menu_buttons
        WHERE id IN (
          SELECT id FROM main_menu_buttons
          WHERE action_type = 'mini_app'
            AND action_value ILIKE '%node.satkaconnect.xyz%'
          OFFSET 1
        );
        """
    )
    print('✓ main_menu_buttons updated')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print('SQL failed:', exc, file=sys.stderr)
        sys.exit(1)
