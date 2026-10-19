FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps ./apps
COPY operia ./operia
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY .env.example ./.env.example

RUN groupadd --gid 10001 operia \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin operia \
    && mkdir -p storage/evidence storage/uploads storage/exports storage/maps storage/temp memory_vault \
    && chown -R 10001:10001 storage memory_vault

USER 10001:10001

EXPOSE 8020

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8020"]

