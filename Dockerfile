FROM --platform=linux/amd64 python:3.8-slim-buster as build


COPY . /app

RUN pip install --upgrade pip

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
