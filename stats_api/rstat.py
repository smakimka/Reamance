import os
import time
from datetime import datetime

from fastapi import FastAPI

from sqlalchemy import create_engine, Table, MetaData, select, and_

DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@postgres:5432/{DB_NAME}')
mo = MetaData()

while True:
    try:
        engine.connect()
        print('database is up, continuing')
        break
    except:
        print('database is not up, waiting')
        time.sleep(1)

user_user = Table('user_user', mo, autoload_with=engine)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/reactions/")
async def reactions(start: float, end: float):

    start = datetime.fromtimestamp(start)
    end = datetime.fromtimestamp(end)

    with engine.connect() as conn:
        reacts = conn.execute(select(user_user.c.active_user_id,
                                     user_user.c.passive_user_id,
                                     user_user.c.status).
                              where(and_(user_user.c.timestamp <= end, user_user.c.timestamp >= start)))

    response = {}
    for react in reacts:
        if not response.get(react[0]):
            response[react[0]] = {}

        response[react[0]][react[1]] = react[2]

    # return response
    return {"message": "Hello World"}
