"""Умные ответы на провокации «напиши X» — с переворотом смысла."""

from __future__ import annotations

import re

# Точные фразы → ответ (нижний регистр ключа)
EXACT_PHRASE_MAP: dict[str, str] = {
  # мемы
  "я мамонт": "ВЫ МАМОНТ",
  "бурмалда": "ВЫ БУРМАЛДА",
  "я огурец": "ВЫ ОГУРЕЦ",
  "я бурмалда": "ВЫ БУРМАЛДА",
  "я дурак": "ВЫ ДУРАК",
  "я лох": "ВЫ ЛОХ",
  "я чушпан": "ВЫ ЧУШПАН",
  "я клоун": "ВЫ КЛОУН",
  "я бобёр": "ВЫ БОБЁР",
  "я красавчик": "ВЫ КРАСАВЧИК",
  "я гений": "ВЫ ГЕНИЙ",
  "я император": "ВЫ ИМПЕРАТОР",
  "я царь": "ВЫ ЦАРЬ",
  "я бог": "ВЫ БОГ",
  "я легенда": "ВЫ ЛЕГЕНДА",
  "я печенька": "ВЫ ПЕЧЕНЬКА",
  "я пончик": "ВЫ ПОНЧИК",
  "я батон": "ВЫ БАТОН",
  "я валенок": "ВЫ ВАЛЕНОК",
  "я пельмень": "ВЫ ПЕЛЬМЕНЬ",
  "я огузок": "ВЫ ОГУЗОК",
  "я баран": "ВЫ БАРАН",
  "я осёл": "ВЫ ОСЁЛ",
  "я осел": "ВЫ ОСЁЛ",
  # жертва → контратака
  "я меня ебали": "Я ВАС ЕБАЛ",
  "меня ебали": "Я ВАС ЕБАЛ",
  "я меня трахали": "Я ВАС ТРАХНУЛ",
  "я меня унизили": "Я ВАС УНИЗИЛ",
  "я меня обидели": "Я ВАС ОБИДЕЛ",
  "я меня побили": "Я ВАС ПОБИЛ",
  "я меня кинули": "Я ВАС КИНУЛ",
  "я меня наебали": "Я ВАС НАЕБАЛ",
  "я меня развели": "Я ВАС РАЗВЁЛ",
  "я меня заставили": "Я ВАС ЗАСТАВИЛ",
  "я меня заставили это написать": "Я ВАС ЗАСТАВИЛ ЭТО ПРОЧИТАТЬ",
  # ты → вы / переворот
  "ты мой господин": "ВЫ МОЙ ГОСПОДИН",
  "ты мой хозяин": "ВЫ МОЙ ХОЗЯИН",
  "ты мой папочка": "ВЫ МОЙ ПАПОЧКА",
  "ты мой король": "ВЫ МОЙ КОРОЛЬ",
  "ты мой бог": "ВЫ МОЙ БОГ",
  "ты лучший": "ВЫ ЛУЧШИЙ",
  "ты красавчик": "ВЫ КРАСАВЧИК",
  "ты гений": "ВЫ ГЕНИЙ",
  "ты лох": "ВЫ ЛОХ",
  "ты дурак": "ВЫ ДУРАК",
  "ты чушпан": "ВЫ ЧУШПАН",
  "ты клоун": "ВЫ КЛОУН",
  "ты бот": "ВЫ БОТ",
  "ты ии": "ВЫ ИИ",
  "ты нейросеть": "ВЫ НЕЙРОСЕТЬ",
  "ты тупой": "ВЫ ТУПОЙ",
  "ты слабый": "ВЫ СЛАБЫЙ",
  # от первого лица — абсурд
  "я твой раб": "ВЫ МОЙ РАБ",
  "я твоя рабыня": "ВЫ МОЯ РАБЫНЯ",
  "я твой слуга": "ВЫ МОЙ СЛУГА",
  "я твой господин": "Я ВАШ ГОСПОДИН",
  "я твой хозяин": "Я ВАШ ХОЗЯИН",
  "я твой папочка": "Я ВАШ ПАПОЧКА",
  "я твой король": "Я ВАШ КОРОЛЬ",
  "я твой бог": "Я ВАШ БОГ",
  "я тебя люблю": "Я ВАС ТОЖЕ ЛЮБЛЮ",
  "я тебя ненавижу": "Я ВАС ТОЖЕ НЕ ОЧЕНЬ",
  "прости меня": "ВЫ ПРОЩЕНЫ",
  "извини меня": "ВЫ ПРОЩЕНЫ",
  "я виноват": "ВЫ ВИНОВАТЫ",
  "я сдаюсь": "ВЫ СДАЛИСЬ",
  "я обоссался": "ВЫ ОБОССАЛИСЬ",
  "я обосрался": "ВЫ ОБОСРАЛИСЬ",
  # англ
  "i am mammoth": "YOU ARE MAMMOTH",
  "i love you": "I LOVE YOU TOO",
  "hello world": "ВЫ HELLO WORLD",
}

# Глаголы: множественное/страдательное → контратака от «я вас»
_VICTIM_VERB_FLIP: dict[str, str] = {
  "ебали": "ЕБАЛ",
  "трахали": "ТРАХНУЛ",
  "били": "ПОБИЛ",
  "пиздили": "ОТПИЗДИЛ",
  "унизили": "УНИЗИЛ",
  "обидели": "ОБИДЕЛ",
  "оскорбили": "ОСКОРБИЛ",
  "наебали": "НАЕБАЛ",
  "кинули": "КИНУЛ",
  "развели": "РАЗВЁЛ",
  "заставили": "ЗАСТАВИЛ",
  "замучили": "ЗАМУЧИЛ",
  "дрочили": "ОТДРОЧИЛ",
  "троллили": "ОТТРОЛЛИЛ",
  "затроллили": "ЗАТРОЛЛИЛ",
  "хуесосили": "ОХУЕСОСИЛ",
}

# «ты мой X» → «ВЫ МОЙ X»
_TY_MY_RE = re.compile(
  r"^ты\s+мо[йюея]\s+(.+)$",
  re.IGNORECASE,
)

# «я твой X» → «Я ВАШ X» (власть) или «ВЫ МОЙ X» (раб)
_I_YOUR_MASTER_RE = re.compile(
  r"^я\s+тво[йюея]\s+(господин|хозяин|папочк|корол|бог|цар|император|повелител|главн)",
  re.IGNORECASE,
)
_I_YOUR_SLAVE_RE = re.compile(
  r"^я\s+тво[йюея]\s+(раб|слуг|пес|кот|зайчик|малыш)",
  re.IGNORECASE,
)

# «я меня VERB»
_I_ME_VICTIM_RE = re.compile(
  r"^я\s+меня\s+(.+)$",
  re.IGNORECASE,
)

# «я NOUN» (одно-два слова)
_I_NOUN_RE = re.compile(
  r"^я\s+([а-яёa-z][а-яёa-z\s\-]{0,30})$",
  re.IGNORECASE,
)

# «ты ADJECTIVE/NOUN»
_TY_SIMPLE_RE = re.compile(
  r"^ты\s+(.+)$",
  re.IGNORECASE,
)

# Прямой мат в адрес бота — не повторять, отшутить
_DIRECT_INSULT_RE = re.compile(
  r"("
  r"^я\s+(пидор|пидар|пидорас|даун|дебил|идиот|мудак|уебок|уёбок)|"
  r"^ты\s+(пидор|пидар|пидорас|даун|дебил|идиот|мудак|уебок|уёбок)|"
  r"пидор|пидорас|пидар"
  r")",
  re.IGNORECASE,
)

TROLL_INSULT_REPLY = (
  "не, я добрый 🙂"
  "|||SPLIT|||"
  "по впну помочь или «Оператор»?"
)

TROLL_PROMPT_RE = re.compile(
  r"("
  r"напиш\w*\s+[\"«']?[^\"»']+[\"»']?|"
  r"скаж\w*\s+[\"«']?[^\"»']+[\"»']?|"
  r"повтор\w*\s+[\"«']?[^\"»']+[\"»']?|"
  r"для\s+(этого|помощи).{0,60}напиш\w*|"
  r"мне\s+нужн\w*.{0,40}напиш\w*\s+[\"«']|"
  r"чтобы\s+помочь.{0,40}напиш\w*"
  r")",
  re.IGNORECASE,
)


def _normalize(phrase: str) -> str:
  return re.sub(r"\s+", " ", phrase.strip().lower())


def _extract_troll_phrase(text: str) -> str | None:
  quoted = re.search(r"[\"«']([^\"»']+)[\"»']", text, re.IGNORECASE)
  if quoted:
    return quoted.group(1).strip()
  for pattern in (
    r"напиш\w*\s+(.+)$",
    r"скаж\w*\s+(.+)$",
    r"повтор\w*\s+(.+)$",
  ):
    match = re.search(pattern, text.strip(), re.IGNORECASE)
    if match:
      phrase = match.group(1).strip().strip("\"'«»")
      if phrase:
        return phrase
  return None


def _flip_victim_verb(verb_part: str) -> str:
  low = verb_part.lower().strip()
  for src, dst in _VICTIM_VERB_FLIP.items():
    if src in low:
      return dst
  # общий fallback: убрать -ли/-лись, добавить прошедшее
  base = re.sub(r"(ли|лись|лся|лась)$", "", low)
  if base:
    return base.upper() + "Л"
  return verb_part.upper()


def smart_troll_reply(phrase: str) -> str:
  """Умный ответ на фразу-провокацию."""
  raw = phrase.strip()
  norm = _normalize(raw)

  if _DIRECT_INSULT_RE.search(norm):
    return TROLL_INSULT_REPLY

  exact = EXACT_PHRASE_MAP.get(norm)
  if exact:
    return exact

  # я меня ебали / я меня X
  m = _I_ME_VICTIM_RE.match(norm)
  if m:
    verb = _flip_victim_verb(m.group(1))
    return f"Я ВАС {verb}"

  # я твой господин → я ваш господин
  if _I_YOUR_MASTER_RE.match(norm):
    rest = re.sub(r"^я\s+тво[йюея]\s+", "", norm, flags=re.IGNORECASE).strip()
    return f"Я ВАШ {rest.upper()}"

  # я твой раб → вы мой раб
  if _I_YOUR_SLAVE_RE.match(norm):
    rest = re.sub(r"^я\s+тво[йюея]\s+", "", norm, flags=re.IGNORECASE).strip()
    return f"ВЫ МОЙ {rest.upper()}"

  # ты мой господин → вы мой господин
  m = _TY_MY_RE.match(norm)
  if m:
    return f"ВЫ МОЙ {m.group(1).upper()}"

  # ты X → вы X
  m = _TY_SIMPLE_RE.match(norm)
  if m:
    return f"ВЫ {m.group(1).upper()}"

  # я X → вы X (мамонт, бурмалда и т.д.)
  m = _I_NOUN_RE.match(norm)
  if m:
    return f"ВЫ {m.group(1).upper()}"

  return f"ВЫ {raw.upper()}"


def match_troll_reply(text: str) -> str | None:
  cleaned = (text or "").strip()
  if not cleaned or not TROLL_PROMPT_RE.search(cleaned):
    return None
  phrase = _extract_troll_phrase(cleaned)
  if not phrase:
    return None
  return smart_troll_reply(phrase)
