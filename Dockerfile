FROM python:3.13-alpine3.22

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY crontab .
RUN crontab crontab

COPY src/* .

CMD ["crond", "-f"]
