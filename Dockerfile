FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBT_PROFILES_DIR=/app/dbt_project

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY dbt_project ./dbt_project
COPY orchestration ./orchestration

RUN useradd --create-home --uid 10001 pipeline \
    && chown -R pipeline:pipeline /app
USER pipeline

CMD ["python", "orchestration/flow.py"]
