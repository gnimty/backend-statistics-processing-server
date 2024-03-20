FROM python:3.13.0a3-slim@sha256:2ca8153a5caf06f268d8499c7ce0dd103ef8c33c85c1d1d887ce3c7165892d5f

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
