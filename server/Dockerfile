FROM python:3.11

RUN apt-get update && apt-get install -y python3-dev && rm -rf /var/lib/apt/lists/*

COPY /server/alembic /server/alembic
COPY /server/application /server/application
COPY /server/__init__.py /server
COPY /server/alembic.ini /server
COPY /server/requirements_prod.txt /server
COPY /server/.env.prod /server

RUN pip install --no-cache-dir -r /server/requirements_prod.txt

RUN usermod -aG root www-data

ENV PYTHONPATH=/server

WORKDIR /server

CMD ["uvicorn", "application.main:app_proj", "--host", "0.0.0.0", "--port", "5000", "--reload"]