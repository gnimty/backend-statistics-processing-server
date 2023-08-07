FROM python:3.9-slim as base

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
