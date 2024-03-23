# FROM python@sha256:0a43b1c192c964971508b745ce5dabb8a5e6cbe6ec4b9d6847092e3336b10b35
# FROM python:3.13.0a3@sha256:a6c6be624456b4a6f20f0b3e19774e5b0f68cd28660b4157fd65f3f3bfcde9b2
FROM python:3.11.8@sha256:47d0618fb878d93e1b8cacb184fd8f727ae95c1b85d5959723e1d3e1848e2aba

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
