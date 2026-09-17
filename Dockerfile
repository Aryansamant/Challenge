FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data ./data
COPY frontend ./frontend
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini .

ENV PYTHONPATH=/app
ENV PORT=8000
EXPOSE 8000

CMD ["python", "-m", "src.api.main"]
