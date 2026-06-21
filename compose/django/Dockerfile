FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps: build tools for psycopg/Pillow + postgres client for backups.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev postgresql-client \
        libjpeg-dev zlib1g-dev curl gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=false
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt; fi

COPY . .

RUN chmod +x compose/django/entrypoint.sh compose/django/start-web.sh \
    && mkdir -p /app/media /app/staticfiles /app/logs

ENTRYPOINT ["/app/compose/django/entrypoint.sh"]
CMD ["/app/compose/django/start-web.sh"]
