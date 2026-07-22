# MaxLooking — лайкер историй через открытые каналы

## Схема работы

```
Каналы (channels.txt + уже подписанные)
    → вступить (auto_join)
    → iter_participants (до 300 чел/канал)
    → getPeerStories у каждого
    → ❤️ лайк (18/час, пауза 2.5–4 мин)
```

## Быстрый старт

```bash
pip install -r requirements.txt
cp accounts.example.json accounts.json
cp config.example.json config.json
```

1. Заполни `accounts.json` (api_id, api_hash, phone)
2. Добавь каналы в `channels.txt` (username без @)
3. Запуск:

```bash
python3 maxlooking.py login
python3 maxlooking.py discover   # только поиск
python3 maxlooking.py run        # поиск + лайки
```

## channels.txt

```
moscowchat
piter_chat
dating_ru
```

Также сканируются **уже подписанные** публичные каналы (`use_joined_public_channels: true`).

## Лимиты (по умолчанию)

| Параметр | Значение |
|----------|----------|
| Лайков/час/аккаунт | 18 |
| Лайков/день/аккаунт | 200 |
| Пауза между лайками | 150–250 сек (~15–20/час) |
| Участников/канал | 300 |
| Каналов за прогон | 15 |

## config.json — каналы

```json
"channels": {
  "enabled": true,
  "channels_file": "channels.txt",
  "auto_join": true,
  "use_joined_public_channels": true,
  "max_participants_per_channel": 300,
  "max_channels_per_run": 15
}
```

## FLOOD_WAIT

При `FLOOD_WAIT` скрипт ждёт автоматически. Лимит 15–20/час снижает частоту ошибок.

## Риски

Массовый парс участников каналов + лайки незнакомцам = риск ограничений @SpamBot. Используй на свой страх и риск.
