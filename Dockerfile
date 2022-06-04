# syntax=docker/dockerfile:1

FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt

RUN apt-get update \
    && apt-get install -y git \
    && apt-get install -y libgdal-dev g++ --no-install-recommends \
    && pip3 install -r requirements.txt

# Update C env vars so compiler can find gdal
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]