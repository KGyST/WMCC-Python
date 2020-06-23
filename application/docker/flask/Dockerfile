FROM python:3.7.5-windowsservercore-ltsc2016

WORKDIR /app

ENV PYTHONUNBUFFERED 1
RUN python -m pip install -U pip setuptools

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install -U --no-cache-dir -r /tmp/requirements.txt

COPY ./src /app

ENTRYPOINT ["python", "app.py"]