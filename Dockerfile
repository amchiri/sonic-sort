FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libchromaprint-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt setup.py ./
COPY src ./src

RUN pip install --no-cache-dir -e .

VOLUME ["/music"]

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

ENTRYPOINT ["python", "-m", "src"]
CMD ["run", "/music", "--dry-run"]
