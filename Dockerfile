FROM --platform=linux/amd64 python:3.8-slim-buster

COPY . /app

RUN pip install --upgrade pip

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "-m", "app"]
