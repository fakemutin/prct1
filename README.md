# MaxLooking — мультиаккаунтный лайкер историй Telegram

Парсит активные истории из ленты каждого аккаунта и ставит реакцию ❤️.

## Быстрый старт

```bash
pip install -r requirements.txt
cp accounts.example.json accounts.json
cp config.example.json config.json
```

Заполните `accounts.json` — `api_id`, `api_hash`, `phone` с https://my.telegram.org

```bash
python3 maxlooking.py login   # код из Telegram для каждого аккаунта
python3 maxlooking.py run       # парсинг + лайки
python3 maxlooking.py check     # проверка @SpamBot
```

## Как работает

1. Каждый аккаунт вызывает `stories.getAllStories` — истории контактов и подписок.
2. Фильтрует уже лайкнутые (`sent_reaction`), свои и просроченные.
3. Ставит ❤️ с ротацией между аккаунтами и случайными паузами.
4. При `FLOOD_WAIT` ждёт указанное время.

## Настройки (`config.json`)

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `max_likes_per_account_per_hour` | 20 | Лимит лайков/час на аккаунт |
| `max_likes_per_account_per_day` | 80 | Лимит лайков/день на аккаунт |
| `min_delay_sec` / `max_delay_sec` | 25 / 75 | Пауза между лайками |
| `use_whitelist_only` | false | Лайкать только из `whitelist.txt` |
| `include_channels` | false | Лайкать истории каналов |

## Важно

- Используйте **прогретые** аккаунты (10–14 дней обычной активности).
- Не поднимайте лимиты резко — начните с дефолтных.
- Userbot нарушает ToS Telegram — риск ограничений на вашей стороне.
