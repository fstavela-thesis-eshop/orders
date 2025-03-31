FROM docker.io/library/python:3.13-slim

WORKDIR /orders

COPY . .

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN pip install pipenv
RUN pipenv install --system --deploy

CMD ["sh", "-c", "alembic upgrade head && cd src && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
