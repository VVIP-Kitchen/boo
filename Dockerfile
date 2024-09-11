FROM python:3.10-slim

WORKDIR /boo

COPY requirements.txt /boo
RUN pip install --no-cache-dir -r requirements.txt

COPY . /boo