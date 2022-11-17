import os

from fastapi import FastAPI

DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')

DB_CONNECTION_STRING = f'postgresql://{DB_USER}:{DB_PASSWORD}@postgres:5432/{DB_NAME}'

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
