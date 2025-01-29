FROM mirror.gcr.io/library/python:3.12

RUN pip install poetry

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONPATH="/app/src:$PYTHONPATH"

ENV LOG_JSON_FORMAT=true

COPY ./environment /app/environment
COPY ./src /app/src
COPY ./tests /app/tests
COPY ./poetry.lock /app
COPY ./pyproject.toml /app

WORKDIR /app

RUN poetry config virtualenvs.create false \
    && poetry install --no-root

EXPOSE 8003
EXPOSE 8001
CMD ["poetry", "run", "uvicorn", "src.main:app", "--app-dir", "./src", "--host", "0.0.0.0", "--port", "8003"]
