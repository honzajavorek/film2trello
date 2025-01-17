FROM python:3.11-slim-buster
RUN python -m pip install -U pip poetry==1.8.5
ENV PORT 8080
RUN mkdir /app
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
COPY . /app
RUN poetry install --no-interaction --no-ansi --no-root --no-dev
CMD poetry run film2trello bot
