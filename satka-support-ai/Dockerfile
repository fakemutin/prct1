FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py llm_client.py message_filters.py prompts.py knowledge_base.py canned_responses.py auth_session.py userbot.py reply_utils.py slang_style.py slang_lexicon.py troll_replies.py ./

RUN mkdir -p sessions

CMD ["python", "-u", "userbot.py"]
