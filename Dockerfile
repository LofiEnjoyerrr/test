FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml .
COPY poetry.lock .
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install