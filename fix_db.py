#!/usr/bin/env python3
"""Починка базы данных бота (duels, users). Запуск: python fix_db.py [путь_к_db]"""
import json
import os
import sqlite3
import sys


def load_db_path():
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        db_file = (cfg.get('db_file') or '').strip()
        if db_file:
            return db_file
    if os.path.exists('bot.db'):
        return 'bot.db'
    return 'data.db'


def migrate_duels(conn):
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='duels'")
    if not c.fetchone():
        print('Таблица duels не найдена — пропуск')
        return
    c.execute('PRAGMA table_info(duels)')
    col_names = {row[1] for row in c.fetchall()}
    if 'creator_id' not in col_names and 'user_id' in col_names:
        print('Переименование user_id → creator_id')
        c.execute('ALTER TABLE duels RENAME COLUMN user_id TO creator_id')
        col_names.add('creator_id')
    required = {
        'creator_id': 'INTEGER',
        'opponent_id': 'INTEGER DEFAULT -1',
        'amount': 'REAL DEFAULT 0',
        'mode': "TEXT DEFAULT 'classic'",
        'status': "TEXT DEFAULT 'waiting'",
        'winner_id': 'INTEGER DEFAULT -1',
        'created_at': 'TIMESTAMP',
        'updated_at': 'TIMESTAMP',
        'elo_creator': 'INTEGER DEFAULT 1200',
        'elo_opponent': 'INTEGER DEFAULT 1200',
        'creator_choice': 'TEXT',
        'opponent_choice': 'TEXT',
    }
    for col, typedef in required.items():
        if col not in col_names:
            print(f'Добавляем колонку duels.{col}')
            c.execute(f'ALTER TABLE duels ADD COLUMN {col} {typedef}')
    c.execute("UPDATE duels SET opponent_id = -1 WHERE opponent_id IS NULL OR opponent_id = 0")
    c.execute("UPDATE duels SET status = 'waiting' WHERE status IS NULL OR status = ''")
    c.execute("UPDATE duels SET mode = 'classic' WHERE mode IS NULL OR mode = ''")
    c.execute(
        "UPDATE duels SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL"
    )
    c.execute(
        "UPDATE duels SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL"
    )
    c.execute(
        "UPDATE duels SET status = 'cancelled' WHERE status = 'waiting' AND creator_id IS NULL"
    )
    c.execute(
        '''
        SELECT creator_id, MAX(id) AS keep_id
        FROM duels
        WHERE status = 'waiting'
          AND (opponent_id IS NULL OR opponent_id IN (-1, 0))
          AND creator_id IS NOT NULL
        GROUP BY creator_id
        HAVING COUNT(*) > 1
        '''
    )
    for row in c.fetchall():
        creator_id, keep_id = row[0], row[1]
        c.execute(
            '''
            SELECT id, amount FROM duels
            WHERE creator_id = ? AND status = 'waiting' AND id != ?
              AND (opponent_id IS NULL OR opponent_id IN (-1, 0))
            ''',
            (creator_id, keep_id),
        )
        for old_id, amount in c.fetchall():
            c.execute('UPDATE users SET balance = balance + ? WHERE chatId = ?', (amount, creator_id))
            c.execute(
                'INSERT INTO transactions (user_id, amount, type, description) VALUES (?,?,?,?)',
                (creator_id, amount, 'duel_refund', f'fix_db: отмена дубля дуэли #{old_id}'),
            )
            c.execute("UPDATE duels SET status = 'cancelled' WHERE id = ?", (old_id,))
            print(f'Отменён дубль дуэли #{old_id}, возврат {amount} ₽ пользователю {creator_id}')
    conn.commit()
    print('✅ Таблица duels исправлена')


def migrate_users(conn):
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in c.fetchall()}
    for col, typedef in [
        ('level', 'INTEGER DEFAULT 1'),
        ('exp', 'INTEGER DEFAULT 0'),
        ('elo_rating', 'INTEGER DEFAULT 1200'),
        ('is_verified', 'INTEGER DEFAULT 0'),
        ('vip_active', 'INTEGER DEFAULT 0'),
    ]:
        if col not in cols:
            print(f'Добавляем колонку users.{col}')
            c.execute(f'ALTER TABLE users ADD COLUMN {col} {typedef}')
    conn.commit()
    print('✅ Таблица users проверена')


def main():
    path = load_db_path()
    if not os.path.exists(path):
        print(f'❌ Файл БД не найден: {path}')
        sys.exit(1)
    print(f'📂 База: {path}')
    conn = sqlite3.connect(path)
    migrate_users(conn)
    migrate_duels(conn)
    conn.close()
    print('🎉 Готово! Перезапустите бота.')


if __name__ == '__main__':
    main()
