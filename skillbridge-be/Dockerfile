FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.0.0 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/src \
    ENVIRONMENT=deployment

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        default-libmysqlclient-dev \
        pkg-config \
    && curl -sSL https://install.python-poetry.org | python3 - --version "$POETRY_VERSION" \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"


COPY pyproject.toml poetry.lock ./

RUN poetry install --no-interaction --no-ansi --no-root --only main

COPY . .

# Copy the .env file
ENV PYTHONPATH="/app/src:$PYTHONPATH"
# Set the environment to production (if applicable)
ENV ENVIRONMENT=deployment

EXPOSE 8002

CMD alembic upgrade head && uvicorn skillbridge.app:app --host 0.0.0.0 --port 8002
