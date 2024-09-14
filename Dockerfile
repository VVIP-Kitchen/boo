FROM python:3.10-slim

WORKDIR /boo
RUN apt-get update
RUN apt-get install -y gcc

COPY requirements.txt /boo
RUN pip install --no-cache-dir -r requirements.txt

COPY . /boo