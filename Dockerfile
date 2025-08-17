FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "django_api_enpoint/manage.py", "runserver", "0.0.0.0:8000"]