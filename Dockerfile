FROM python:3.13-alpine AS builder

ENV PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PATH="/root/.local/bin:$PATH:/opt/poetry/bin:$PATH"

RUN apk update && apk add --no-cache curl build-base

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main


FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1

RUN addgroup -g 1000 botuser && \
    adduser -u 1000 -G botuser -h /app -D botuser

WORKDIR /app

COPY --from=builder --chown=botuser:botuser /app/.venv ./.venv
COPY --chown=botuser:botuser app ./app
COPY --chown=botuser:botuser scripts ./scripts

USER botuser

CMD [".venv/bin/python", "-m", "app.main"]
