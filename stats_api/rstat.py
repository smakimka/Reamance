import os
import time
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException

from sqlalchemy import create_engine, Table, MetaData, select, or_, and_
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
        reacts = conn.execute(select(user_user.c.active_user_id,
                                     user_user.c.passive_user_id,
                                     user_user.c.status,
                                     user_user.c.timestamp).
                              where(and_(user_user.c.timestamp <= end, user_user.c.timestamp >= start)))

        reacts = [[react[0], react[1], react[2], react[3]] for react in reacts]
        for react in reacts:
            react[0] = conn.execute(select(users.c.username).where(users.c.id == react[0])).first()[0]
            react[1] = conn.execute(select(users.c.username).where(users.c.id == react[1])).first()[0]

    response = {}
    for react in reacts:
        if not response.get(react[0]):
            response[react[0]] = {}

        response[react[0]][react[1]] = {'value': react[2], 'timestamp': react[3]}

    return response


@app.get("reactions/user/{user_login}/")
async def reactions(user_login: str, access_token: str | None = Header(default=None)):
    if not access_token or access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=404, detail='**** you')

    with engine.connect() as conn:
        user_id = conn.execute(select(users.c.id).where(users.c.username == user_login)).first()
        if user_id:
            user_id = user_id[0]
        else:
            raise HTTPException(status_code=400, detail='No such user')

        reacts = conn.execute(select(user_user.c.active_user_id,
                                     user_user.c.passive_user_id,
                                     user_user.c.status,
                                     user_user.c.timestamp).
                              where(or_(user_user.c.active_user_id == user_id,
                                        user_user.c.passive_user_id == user_id)))

        like_values = ('dislike', 'anonim', 'like')

        user_reacts = {}
        responses = {}
        user_login = conn.execute(select(users.c.username).where(users.c.id == user_id)).first()[0]
        for react in reacts:
            if react[0] == user_id:
                user_reacts[user_login] = {'value': like_values[react[2]], 'timestamp': react[3]}
            else:
                resp_user_login = conn.execute(select(users.c.username).where(users.c.id == react[0])).first()[0]
                responses[resp_user_login] = {'value': like_values[react[2]], 'timestamp': react[3]}

    likes = []
    matches = []
    dislikes = []

    for response, response_info in responses.items():
        if response_info['value'] == 'like' or response_info['value'] == 'anonim':
            if user_reacts.get(response) is not None and \
                    (user_reacts[response]['value'] == 'like' or user_reacts[response]['value'] == 'anonim'):
                matches.append(response)
            else:
                likes.append(response)

        else:
            dislikes.append(response)

    return {'likes': {'count': len(likes), 'users': likes},
            'matches': {'count': len(matches), 'users': matches},
            'dislikes': {'count': len(dislikes), 'users': dislikes}}
