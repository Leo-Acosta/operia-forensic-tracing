FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps ./apps
COPY operia ./operia
COPY storage/.gitkeep ./storage/.gitkeep
COPY .env.example ./.env.example

RUN mkdir -p storage/evidence storage/uploads storage/exports storage/maps storage/temp

EXPOSE 8020

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8020"]

