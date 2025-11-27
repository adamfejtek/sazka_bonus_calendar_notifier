FROM python:3.13-alpine3.22

WORKDIR /app

COPY crontab .
COPY requirements.txt .
COPY src/* .

RUN pip install -r requirements.txt
RUN crontab crontab

CMD ["crond", "-f"]
