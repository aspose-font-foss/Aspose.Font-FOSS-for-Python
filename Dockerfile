FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY pyproject.toml setup.py README.md LICENSE.txt ./
COPY src ./src
COPY tests ./tests
COPY testdata ./testdata
COPY website/generated ./website/generated

RUN python -m pip install --no-cache-dir ".[dev]"

CMD ["python", "-m", "pytest"]
