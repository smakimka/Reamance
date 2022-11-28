import os
from dotenv import load_dotenv

from markup import Markup
from datetime import timedelta

load_dotenv()
# DB
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')

DB_CONNECTION_STRING = f'postgresql://{DB_USER}:{DB_PASSWORD}@postgres:5432/{DB_NAME}'

NAME_MAX_LEN = 100
DESCRIPTION_MAX_LEN = 1024
INTEREST_MAX_LEN = 50


# Bot
bot_token = os.getenv('BOT_TOKEN')

# Statuses
NEW = 0
NAME = 1
AGE = 2
FACULTY = 3
YEAR = 4
DESCRIPTION = 5
INTERESTS = 6
SEX = 7
SEX_PREFERENCES = 8
AGE_PREFERENCES = 9
PHOTO = 10

CONFIRMATION = 11

MAIN_MENU = 12

EDIT_NAME = 13
EDIT_AGE = 14
EDIT_FACULTY = 15
EDIT_YEAR = 16
EDIT_DESCRIPTION = 17
EDIT_INTERESTS = 18
EDIT_SEX = 19
EDIT_SEX_PREFERENCES = 20
EDIT_AGE_PREFERENCES = 21
EDIT_PHOTO = 22

# Sexes
M = 0
F = 1

# Sex preferences
SHOW_MALE = 0
SHOW_FEMALE = 1
SHOW_BOTH = 2

# Likes
DISLIKE = 0
ANONIMOS = 1
LIKE = 2


faculties = ['ВИШ "НМиТ"', 'ВШКМиС', 'ВШБиЭ', 'ВШФ', 'ВШМ', 'ВШП', 'ВШСГН', 'ВШКИ', 'ВШ "Форсайт"',
             'Институт "Первая Академия медиа"', 'Капитаны']

years = [str(y) for y in range(1, 5)]

stop_keyword = 'Готово'
agreed_keyword = 'Согласен'

interests = ['Настольный теннис',
             'Компьютерные игры',
             'Фильмы',
             'Музыка',
             'Футбол',
             'Бизнес',
             'Программирование',
             'Баскетбол',
             'Экономика',
             'Политика',
             'Рыбалка',
             'Аниме',
             'Настольные игры',
             'Технологии',
             'Крипта',
             'Кофе',
             'Искусство',
             'Выставки',
             'Мода',
             'Дизайн',
             'Excel',
             'Сноуборд',
             'Машины',
             'Волонтерство',
             'Танцы',
             'Прогулки'
             ]

interests.sort()
MAX_INTERESTS = 10

sexes = ['Мужской', 'Женский']
sexes_dict = {s: i for i, s in enumerate(sexes)}

sex_prefs = ['Парней', 'Девушек', 'Всех']
sex_prefs_dict = {sp: i for i, sp in enumerate(sex_prefs)}

min_user_age = 16

ages_split = '-'
max_age_diff = 5

admin_group_chat_id = -1001844047419
admin_approval_markup = Markup([['Пойдет', 'Нахуй']])
admin_approval_caption = 'Новый чёрт залетел'
approval_caption = 'Одобрен'
disapproval_caption = 'Послан нахуй'

positive_approval_callback = 'positive_approval'
negative_approval_callback = 'negative_approval'

edit_profile_callback = 'edit_profile'
edit_data_callback = 'edit_data'
back_to_edit_callback = 'back_to_edit'
swipe_callback = 'swipe'
show_profile_callback = 'show_profile'
like_reply_callback = 'like_reply'

main_menu_callback = 'main_menu'

ban_duration = timedelta(days=1)
max_ban_count = 5


def get_profile_caption(user, with_tg=True):
    return f'''{user.name}, {user.age}, {user.faculty}, {user.year}й курс
    
{user.description}

Интересы: {user.interests_str}    
{'Телеграм:' + user.username if with_tg else ''}  
'''


def get_interests_text(user, msg, with_prompt=True):
    user_interests = user.get_interests_list()
    interests_list = []
    if with_prompt:
        interests_list.append('Выбери из списка или напиши сам\n')

    interest_list = [f'Твои интересы ({len(user_interests)}/{MAX_INTERESTS}):']
    for i, interest in enumerate(user_interests, start=1):
        interest_list.append(f'{i}. {interest}')
    interest_list.append(f'\n{msg}')

    return '\n'.join(interest_list)


edit_profile_markup = Markup([['Имя', 'Возраст'],
                              ['Факультет', 'Курс'],
                              ['Описание', 'Интересы'],
                              ['Пол', 'Предпочтения по полу'],
                              ['Предпочтения по возрасту', 'Фото'],
                              ['Изменить видимость анкеты']])
swipe_markup = Markup([['❤', '🖤', '❌']])

like_text = '#like\nТебе поставили лайк! Нажми на кнопку и узнай кто это.'
like_markup = Markup([['Посмотреть']])

match_text = '#match\nДля тебя нашлась пара'
match_markup = Markup([['Посмотреть']])

like_reply_markup = Markup([['❤', '❌']])

items_in_page = 5
if len(faculties) % items_in_page == 0:
    last_faculty_page = len(faculties) // items_in_page
else:
    last_faculty_page = len(faculties) // items_in_page + 1


edit_profile_phrase = 'Редактировать анкету'
start_swiping_phrase = 'Оценить новые анкеты'

edit_profile_phrases = {'name': 'Введи новое имя',
                        'age': 'Введи новый возраст',
                        'faculty': 'Выбери новый факультет',
                        'year': 'Выбери новый курс',
                        'description': 'Напиши новое описание',
                        'interests': 'Выбирай новые интрересы (можешь написать свой)',
                        'sex': 'Выбирай пол',
                        'sex_preferences': 'Выбирай кого хочешь видеть',
                        'age_preferences': 'Напиши, людей какого возраста ты хочешь видеть? Напиши диапазон через "-"\nНапример: (19-21)',
                        'photo': 'Скидывай новую фотку'}
after_edit_markup = Markup([['<<', 'Главное меню']])
main_menu_markup = Markup([[start_swiping_phrase, edit_profile_phrase]]).reply

replies = {
    'terms': {'text': 'Привет\! Рад видеть тебя в дейтинг боте для студентов РЭУ Плеханова\.\n\n'
                      'Совсем скоро перейдем к созданию твоей анкеты, надо только разобраться с юридическими формальностями\n\n'
                      'Чтобы пользоваться ботом, надо быть согласным с нашими правилами сообщества, политикой конфиденциальности и условиями пользования\. Все эти документы можно найти на этой [странице](https://www.notion.so/Legal-Reamance-bot-57772b2752ad43a29e3a4a8def811159)',
              'markup': Markup([[agreed_keyword]])},
    'name': {'text': 'Отлично, давай заполним твою анкету, как тебя зовут?',
             'markup': None},
    'age': {'text': 'Сколько лет тебе?',
            'markup': None},
    'faculty': {'text': 'Старость не радость..., с какого ты факультета?',
                'markup': Markup([[f] for f in faculties])},
    'year': {'text': 'C какого ты курса?',
             'markup': Markup([years])},
    'description': {'text': 'Круто,  расскажи о себе, это будет в твоей анкете. Оптимальная длина - 1-2 предложения.',
                    'markup': None},
    'interests': {'text': 'Миленько, что тебе нравится?\nЕсли в списке чего-то нет, можешь написать'},
    'sex': {'text': 'Ok, выбери свой пол',
            'markup': Markup([[s for s in sexes]])},
    'sex_preferences': {'text': 'Выбери, кого ты хочешь видеть',
                        'markup': Markup([[sp for sp in sex_prefs]])},
    'age_preferences': {'text': 'Людей какого возраста ты хочешь видеть? Напиши диапазон через "-"\nНапример: (19-21)',
                        'markup': None},
    'photo': {'text': 'Понятно, скинь фотку',
              'markup': None},
    'confirmation': {'text': 'Отлично, осталось только отправить фотку своего студака (личную инфу можешь замазать) и подождать подтверждения, я тебе сообщу',
                     'markup': None},
    'positive_approval': {'text': 'Поздравляю, твою завявку одобрили, добро пожаловать)\n❤ - лайк \n🖤 - анонимный лайк \n❌ - дизлайк\nУдачи!', 'markup': main_menu_markup},

    'negative_approval': 'Твою заявку не одобрили, отправь ещё раз, только нормально',

    'after_sex_prefs': 'Я буду показывать тебе {0}',
    'after_sex': 'Твой пол: {0}',
    'after_faculty': 'Значит, {0}, хорошо',
    'after_year': 'Мммм, {0} курс',
    'after_edit': 'Готово.',
    'next_interest_str': 'А ещё?',
    'wrong_input': '😑',
    'image': 'Поставь пж галочку при загрузке)',
    'unexpected_photo': 'А эта фотка к чему?',
    'waiting_for_confirmation': 'Подтверждение обычно занимает не долго, подожди',
    'already_has_interest': 'Повторяешься)',
    'too_much_interests': 'Ты и так оченб интересный, хватит',
    'no_more_matches': 'Сори, но люди. подходящие твоим запросам закончились :(',
    'banned': 'Тебе выдан бан на день, сиди жди теперь',
    'need_to_be_visible': 'Чтобы смотреть анкеты сначала сделай свою анкету видимой',
    'now_invisible': 'Теперь ты невидимка',
    'now_visible': 'Теперь тебя снова видно',
}


def get_wrong_len_reply(length, right_length):
    return f'Тут слишком много симвлов ({length}), максимум - {right_length}'
