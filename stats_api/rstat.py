import os
import time
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException

from sqlalchemy import create_engine, Table, MetaData, select, and_
from dotenv import load_dotenv


load_dotenv()
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

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

users = Table('users', mo, autoload_with=engine)
user_user = Table('user_user', mo, autoload_with=engine)


app = FastAPI()


@app.get("/reactions/")
async def reactions(start: float, end: float, access_token: str | None = Header(default=None)):
    if not access_token or access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=404, detail="**** you")

    start = datetime.fromtimestamp(start)
    end = datetime.fromtimestamp(end)

    with engine.connect() as conn:
        test = conn.execute(select(user_user.c.active_user_id,
                                     user_user.c.passive_user_id,
                                     user_user.c.status))
        for react in test:
            print(react)

        return {}
        reacts = conn.execute(select(user_user.c.active_user_id,
                                     user_user.c.passive_user_id,
                                     user_user.c.status).
                              where(and_(user_user.c.timestamp <= end, user_user.c.timestamp >= start)))

        for react in reacts:
            print(react)

        reacts = [[react[0], react[1], react[2]] for react in reacts]
        for react in reacts:
            react[0] = conn.execute(select(users.c.username).where(users.c.id == react[0])).first()[0]
            react[1] = conn.execute(select(users.c.username).where(users.c.id == react[1])).first()[0]

    response = {}
    for react in reacts:
        if not response.get(react[0]):
            response[react[0]] = {}

        response[react[0]][react[1]] = react[2]

    return response
