FROM python:3.9.17-slim@sha256:624ca123d5e35b2662282dde1e736404bf8fed72125745260f7a4dbb0b860a63

COPY . /app

RUN pip install --upgrade pip

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
