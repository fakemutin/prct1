# MaxLooking — мультиаккаунтный лайкер историй Telegram

Парсит **публичные истории незнакомцев** через глобальный поиск Telegram и ставит ❤️.

## Быстрый старт

```bash
pip install -r requirements.txt
cp accounts.example.json accounts.json
cp config.example.json config.json
python3 maxlooking.py login
python3 maxlooking.py discover   # только поиск (без лайков)
python3 maxlooking.py run        # поиск + лайки
python3 maxlooking.py check      # @SpamBot
```

## Откуда берутся истории

| Источник | API | Кто попадает |
|----------|-----|--------------|
| Хештеги (#москва, #россия...) | `stories.searchPosts` | Публичные истории незнакомцев с хештегом |
| Люди рядом | `contacts.getLocated` | Кто сам включил геолокацию в Telegram |
| Лента (опц.) | `stories.getAllStories` | Контакты и подписки (`use_feed: true`) |

По умолчанию: **только незнакомцы** (`skip_contacts: true`), **только юзеры** (`users_only: true`).

## RU-фильтр

Прокси-признаки «русскоязычный пользователь» (100% точности нет):
- `lang_code`: ru, uk, be, kk
- телефон +7
- кириллица в имени

**Возраст 18+ через API определить нельзя** — Telegram не отдаёт дату рождения.

## Настройки discovery (`config.json`)

```json
"discovery": {
  "enabled": true,
  "use_feed": false,
  "skip_contacts": true,
  "russian_filter": true,
  "hashtags": ["москва", "спб", "россия"],
  "max_pages_per_hashtag": 5,
  "people_nearby": true
}
```

## Лимиты

- 20 лайков/час, 80/день на аккаунт (меняйте в `config.json`)
- Пауза 25–75 сек между лайками
- При `FLOOD_WAIT` — автоматическое ожидание

## Риски

Userbot + массовые лайки незнакомцам = высокий риск ограничений. Прогревайте аккаунты 10–14 дней.
