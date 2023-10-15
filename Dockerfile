FROM python:3.11

ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN pip install --upgrade pip

COPY requirements.txt /code/

RUN pip install -r requirements.txt

COPY ./avito_parser /code/avito_parser/
COPY ./migrations /code/migrations/
COPY ./database /code/database/
COPY ./bot /code/bot/
COPY main.py /code/
COPY alembic.ini /code/
