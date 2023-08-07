FROM python:latest@sha256:0a43b1c192c964971508b745ce5dabb8a5e6cbe6ec4b9d6847092e3336b10b35

COPY . /app

RUN pip install --upgrade pip

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
