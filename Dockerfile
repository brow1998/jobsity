FROM python:latest

COPY requirements.txt requirements.txt
COPY consumer.py consumer.py
RUN pip install -r requirements.txt
CMD python consumer.py