import os
import json
import base64

from dotenv import load_dotenv
from datetime import datetime
from random import randint, choice
from sqlalchemy import MetaData, Table, create_engine, insert

load_dotenv()


def main():
    mo = MetaData()
    engine = create_engine(os.getenv('DB_CONNECTION_STRING'))

    users = Table('users', mo, autoload_with=engine)
    users_interests = Table('users_interests', mo, autoload_with=engine)

    names = []
    with open('names.jsonl', 'r', encoding='utf-8') as file:
        for line in file.readlines():
            names.append(json.loads(line)['text'])

    with open('quotes.json', 'r', encoding='utf-8') as file:
        quotes = json.load(file)

    with engine.connect() as conn:
        users_ids = []
        for i in range(1_000):
            print(f'generating user {i}')
            chat_id = randint(100_000_000, 999_999_999)
            min_age = randint(16, 22)
            animal = choice(os.listdir("animals"))
            with open(f'animals/{animal}/{choice(os.listdir(f"animals/{animal}"))}', 'rb') as file:
                photo = base64.b64encode(file.read()).decode()

            user_entry = conn.execute(insert(users).values({
                'chat_id': chat_id,
                'status': 12,
                'visible': True,
                'reg_timestamp': datetime.now(),
                'username': f'@{names[i]}{chat_id}',
                'name': names[i],
                'sex': choice([0, 1]),
                'age': randint(16, 22),
                'faculty': choice(['ВИШ "НМиТ"', 'ВШКМиС', 'ВШБиЭ', 'ВШФ', 'ВШМ', 'ВШП', 'ВШСГН', 'ВШКИ', 'ВШ "Форсайт"',
                                   'Институт "Первая Академия медиа"', 'Капитаны']),
                'year': choice([1, 2, 3, 4]),
                'description': quotes[i]['Quote'],
                'sex_preferences': choice([0, 1, 2]),
                'min_age': min_age,
                'max_age': min_age + randint(0, 3),
                'photo': photo,
                'ban_count': 0,
            }))
            users_ids.append(user_entry.inserted_primary_key[0])


if __name__ == '__main__':
    main()
