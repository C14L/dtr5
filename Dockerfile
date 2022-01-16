# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY ./dtr5 /code/
COPY ./dtr5app /code/
COPY ./manage.py /code/
COPY ./static /code/
COPY ./test_toolbox.py /code/
COPY ./toolbox_imgur.py /code/
COPY ./toolbox.py /code/
COPY ./simple_reddit_oauth /code/
