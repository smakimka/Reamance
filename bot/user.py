from sqlalchemy import select, update, insert, delete, func, and_
from dataclasses import dataclass

from datetime import datetime

import config


class User:
    def __init__(self, mo, conn, chat_id):
        self.users = mo.tables['users']
        self.interests = mo.tables['interests']
        self.users_interests = mo.tables['users_interests']
        self.user_user = mo.tables['user_user']

        self.conn = conn
        self.chat_id = chat_id

        self.id = None
        self.status = None
        self.visible = None
        self.reg_timestamp = None
        self.name = None
        self.sex = None
        self.age = None
        self.faculty = None
        self.year = None
        self.description = None
        self.sex_preferences = None
        self.active_msg_id = None
        self.photo = None
        self.min_age = None
        self.max_age = None
        self.ban_count = None
        self.ban_timestamp = None
        self.username = None
        self.page = None

        self._init()
        self.changed = False

    @property
    def interests_str(self):
        return self._get_interests_str()

    def _init(self):
        user = self.conn.execute(select(self.users.c.id,
                                        self.users.c.status,
                                        self.users.c.visible,
                                        self.users.c.reg_timestamp,
                                        self.users.c.name,
                                        self.users.c.sex,
                                        self.users.c.age,
                                        self.users.c.faculty,
                                        self.users.c.year,
                                        self.users.c.description,
                                        self.users.c.sex_preferences,
                                        self.users.c.active_msg_id,
                                        self.users.c.photo,
                                        self.users.c.min_age,
                                        self.users.c.max_age,
                                        self.users.c.ban_count,
                                        self.users.c.ban_timestamp,
                                        self.users.c.username,
                                        self.users.c.page,
                                        ).
                                 where(self.users.c.chat_id == self.chat_id)).first()

        if user:
            self.id = user[0]
            self.status = user[1]
            self.visible = user[2]
            self.reg_timestamp = user[3]
            self.name = user[4]
            self.sex = user[5]
            self.age = user[6]
            self.faculty = user[7]
            self.year = user[8]
            self.description = user[9]
            self.sex_preferences = user[10]
            self.active_msg_id = user[11]
            self.photo = user[12]
            self.min_age = user[13]
            self.max_age = user[14]
            self.ban_count = user[15]
            self.ban_timestamp = user[16]
            self.username = user[17]
            self.page = user[18]
        else:
            self.status = 0
            self.visible = True
            self.reg_timestamp = datetime.now()
            self.ban_count = 0
            self.page = 0

            user_id = self.conn.execute(insert(self.users).values({
                'chat_id': self.chat_id,
                'status': self.status,
                'visible': self.visible,
                'reg_timestamp': self.reg_timestamp,
                'ban_count': self.ban_count,
                'ban_timestamp': datetime(year=2000, month=1, day=1),
                'page': self.page,
            }))
            self.id = user_id.inserted_primary_key[0]

    def __enter__(self):
        return self

    def __setattr__(self, key, value):
        super().__setattr__('changed', True)
        super().__setattr__(key, value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.changed:
            self.sync()

    def add_interest(self, interest):
        user_interests = self.get_interests_list()
        if len(user_interests) >= config.MAX_INTERESTS:
            return 'too_much'

        if interest in user_interests:
            return 'already has'

        db_interest = self.conn.execute(select(self.interests.c.id).
                                        where(self.interests.c.interest == interest)).first()
        if db_interest:
            self.conn.execute(insert(self.users_interests).values({
                'interest_id': db_interest[0],
                'user_id': self.id,
            }))
        else:
            db_interest = self.conn.execute(insert(self.interests).values({
                'interest': interest
            }))

            self.conn.execute(insert(self.users_interests).values({
                'interest_id': db_interest.inserted_primary_key[0],
                'user_id': self.id,
            }))
        return 'ok'

    def _get_interests_str(self):
        interests_list = []
        interests = self.conn.execute(select(self.interests.c.interest).join(self.interests).select_from(self.users_interests).
                                      where(self.users_interests.c.user_id == self.id))
        for interest in interests:
            interests_list.append(interest[0])
        if interests_list:
            return ', '.join(interests_list)
        else:
            return '-'

    def get_interests_list(self):
        interests_list = []
        interests = self.conn.execute(select(self.interests.c.interest).join(self.interests).select_from(self.users_interests).
                                      where(self.users_interests.c.user_id == self.id))
        for interest in interests:
            interests_list.append(interest[0])
        return interests_list

    def clear_interests(self):
        self.conn.execute(delete(self.users_interests).where(self.users_interests.c.user_id == self.id))

    def get_next_match(self):
        match = self.conn.execute(select(self.users.c.id,
                                         self.users.c.chat_id,
                                         self.users.c.name,
                                         self.users.c.age,
                                         self.users.c.faculty,
                                         self.users.c.year,
                                         self.users.c.description,
                                         self.users.c.photo,
                                         self.users.c.username).
                                  where(and_(self.users.c.id != self.id,
                                             self.users.c.id.not_in(select(self.user_user.c.passive_user_id).
                                                                    where(self.user_user.c.active_user_id == self.id)))).
                                  order_by(func.random()).
                                  limit(1)).first()

        passive_user_id = match[0]

        interests_list = []
        interests = self.conn.execute(
            select(self.interests.c.interest).join(self.interests).select_from(self.users_interests).
            where(self.users_interests.c.user_id == passive_user_id))
        for interest in interests:
            interests_list.append(interest[0])
        if interests_list:
            interests_str = ', '.join(interests_list)
        else:
            interests_str = '-'

        return ProfileData(
            id=passive_user_id,
            chat_id=match[1],
            name=match[2],
            age=match[3],
            faculty=match[4],
            year=match[5],
            description=match[6],
            photo=match[7],
            username=match[8],
            interests_str=interests_str,
        )

    def insert_like(self, passive_user_id, like_value):
        self.conn.execute(insert(self.user_user).values({
            'active_user_id': self.id,
            'passive_user_id': passive_user_id,
            'status': like_value,
        }))

    def like(self, passive_user_id, like_value):
        self.insert_like(passive_user_id, like_value)

        passive_user_like_value = self.conn.execute(select(self.user_user.c.status).
                                                    where(and_(self.user_user.acive_user_id == passive_user_id,
                                                               self.user_user.passive_user_id == self.id))).first()

        if passive_user_like_value:
            if like_value > config.DISLIKE and passive_user_like_value[0] > config.DISLIKE:
                return 'match'
            elif like_value == config.LIKE:
                return 'like'
        else:
            if like_value == config.LIKE:
                return 'like'
        return 'no_event'

    def sync(self):
        self.conn.execute(update(self.users).values({
            'chat_id': self.chat_id,
            'status': self.status,
            'visible': self.visible,
            'name': self.name,
            'sex': self.sex,
            'age': self.age,
            'faculty': self.faculty,
            'year': self.year,
            'description': self.description,
            'sex_preferences': self.sex_preferences,
            'active_msg_id': self.active_msg_id,
            'photo': self.photo,
            'min_age': self.min_age,
            'max_age': self.max_age,
            'ban_count': self.ban_count,
            'ban_timestamp': self.ban_timestamp,
            'username': self.username,
            'page': self.page,

        }).where(self.users.c.id == self.id))


@dataclass
class ProfileData:
    id: int
    chat_id: int
    name: str
    age: int
    faculty: str
    year: int
    description: str
    photo: str
    interests_str: str
    username: str
