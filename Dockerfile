FROM python:slim-bullseye

COPY . /app

RUN pip install --upgrade pip

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
