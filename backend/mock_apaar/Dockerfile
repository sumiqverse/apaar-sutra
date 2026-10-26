FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic httpx

COPY mock_apaar /app/mock_apaar
COPY data/apaar_registry.json /app/data/apaar_registry.json

EXPOSE 8001

CMD ["uvicorn", "mock_apaar.server:mock_apaar_app", "--host", "0.0.0.0", "--port", "8001"]
