FROM python:3.6.7-alpine3.7

RUN mkdir /code

WORKDIR /code

RUN apk add postgresql-dev libffi-dev build-base musl-dev
RUN apk add linux-headers

ADD requirements.txt .

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

RUN pip install -r requirements.txt

EXPOSE 3031

ADD dev .
COPY gsheets ./gsheets
