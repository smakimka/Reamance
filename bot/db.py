from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, insert

from config import DB_CONNECTION_STRING, interests, NAME_MAX_LEN, DESCRIPTION_MAX_LEN, INTEREST_MAX_LEN


def main():
    engine = create_engine(DB_CONNECTION_STRING)

    mo = MetaData()

    users_table = Table('users', mo,
          Column('id', Integer, primary_key=True, autoincrement=True),
          Column('chat_id', Integer, nullable=False),
          Column('status', Integer, nullable=False, default=0),
          Column('visible', Boolean, nullable=False, default=True),
          Column('reg_timestamp', DateTime, nullable=False),
          Column('username', String(1024), nullable=True),
          Column('name', String(NAME_MAX_LEN), nullable=True),
          Column('sex', Integer, nullable=True),
          Column('age', Integer, nullable=True),
          Column('faculty', String(50), nullable=True),
          Column('year', Integer, nullable=True),
          Column('description', String(DESCRIPTION_MAX_LEN), nullable=True),
          Column('sex_preferences', Integer, nullable=True),
          Column('active_msg_id', Integer, nullable=True),
          Column('photo', Text, nullable=True),
          Column('min_age', Integer, nullable=True),
          Column('max_age', Integer, nullable=True),
          Column('ban_count', Integer, nullable=True),
          Column('ban_timestamp', DateTime, nullable=True),
          Column('page', Integer, nullable=True),

          )

    interests_table = Table('interests', mo,
          Column('id', Integer, primary_key=True, autoincrement=True),
          Column('interest', String(INTEREST_MAX_LEN), nullable=False),
          )

    users_interests_table = Table('users_interests', mo,
          Column('id', Integer, primary_key=True, autoincrement=True),
          Column('user_id', ForeignKey('users.id'), nullable=False),
          Column('interest_id', ForeignKey('interests.id'), nullable=False),
          )

    user_user = Table('user_user', mo,
                      Column('id', Integer, primary_key=True, autoincrement=True),
                      Column('active_user_id', ForeignKey('users.id'), nullable=False),
                      Column('passive_user_id', ForeignKey('users.id'), nullable=False),
                      Column('status', Integer, nullable=False),
                      )

    with engine.connect() as conn:
        mo.drop_all(conn)
        mo.create_all(conn)

        for interest in interests:
            conn.execute(insert(interests_table).values({
                'interest': interest
            }))
