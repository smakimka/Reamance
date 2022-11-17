import logging
from io import BytesIO
import base64
import copy
from datetime import datetime
import time

import telegram
from sqlalchemy import create_engine, MetaData, Table, inspect

from telegram import Update, ReplyKeyboardRemove, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters

import config
from db import main as init_database
from user import User
from markup import Markup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# init db
mo = MetaData()
engine = create_engine(config.DB_CONNECTION_STRING)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    with engine.connect() as conn:
        with User(mo, conn, message.from_user.id) as user:
            if user.status != config.NEW:
                user.status = config.NEW
                user.username = message.from_user.name
                await message.reply_text('Начнем сначала', reply_markup=ReplyKeyboardRemove())

            keyboard = copy.deepcopy(config.replies['terms']['markup'])
            keyboard.add_callback(0, 0, f'{config.edit_data_callback}:confirmed')

            start_msg = await message.reply_text(text=config.replies['terms']['text'],
                                                 reply_markup=keyboard.inline,
                                                 parse_mode=ParseMode.MARKDOWN_V2)
            user.active_msg_id = start_msg.id


async def send_reply(message, reply_key):
    if config.replies[reply_key]['markup']:
        await message.reply_text(text=config.replies[reply_key]['text'],
                                 reply_markup=config.replies[reply_key]['markup'])
    else:
        await message.reply_text(text=config.replies[reply_key]['text'], reply_markup=ReplyKeyboardRemove())


async def still_banned(user, bot):
    if user.ban_timestamp < datetime.now():
        user.ban_count = 0
        return False

    await bot.send_message(user.chat_id, config.replies['banned'])
    return True


def build_after_edit_keyboard():
    keyboard = copy.deepcopy(config.after_edit_markup)
    keyboard.add_callback(0, 0, f'{config.back_to_edit_callback}')
    keyboard.add_callback(0, 1, f'{config.main_menu_callback}')
    return keyboard.inline


def build_edit_profile_keyboard():
    keyboard = copy.deepcopy(config.edit_profile_markup)
    keyboard.add_callback(0, 0, f'{config.edit_profile_callback}:name')
    keyboard.add_callback(0, 1, f'{config.edit_profile_callback}:age')
    keyboard.add_callback(1, 0, f'{config.edit_profile_callback}:faculty')
    keyboard.add_callback(1, 1, f'{config.edit_profile_callback}:year')
    keyboard.add_callback(2, 0, f'{config.edit_profile_callback}:description')
    keyboard.add_callback(2, 1, f'{config.edit_profile_callback}:interests')
    keyboard.add_callback(3, 0, f'{config.edit_profile_callback}:sex')
    keyboard.add_callback(3, 1, f'{config.edit_profile_callback}:sex_preferences')
    keyboard.add_callback(4, 0, f'{config.edit_profile_callback}:age_preferences')
    keyboard.add_callback(4, 1, f'{config.edit_profile_callback}:photo')
    keyboard.add_callback(5, 0, f'{config.edit_profile_callback}:visible')

    return keyboard.inline


def build_swipe_keyboard(profile_data):
    keyboard = copy.deepcopy(config.swipe_markup)
    keyboard.add_callback(0, 0, f'{config.swipe_callback}:{profile_data.id}:{config.LIKE}:{profile_data.chat_id}')
    keyboard.add_callback(0, 1, f'{config.swipe_callback}:{profile_data.id}:{config.ANONIMOS}:{profile_data.chat_id}')
    keyboard.add_callback(0, 2, f'{config.swipe_callback}:{profile_data.id}:{config.DISLIKE}:{profile_data.chat_id}')
    return keyboard.inline


def build_like_markup(user):
    keyboard = copy.deepcopy(config.like_markup)
    keyboard.add_callback(0, 0, f'{config.show_profile_callback}:{user.chat_id}:like')
    return keyboard.inline


def build_match_markup(user_chat_id):
    keyboard = copy.deepcopy(config.match_markup)
    keyboard.add_callback(0, 0, f'{config.show_profile_callback}:{user_chat_id}:match')
    return keyboard.inline


def build_like_reply_markup(user_chat_id):
    keyboard = copy.deepcopy(config.like_reply_markup)
    keyboard.add_callback(0, 0, f'{config.like_reply_callback}:{user_chat_id}:like')
    keyboard.add_callback(0, 1, f'{config.like_reply_callback}:{user_chat_id}:dislike')
    return keyboard.inline


def collect_name(user: User, message: telegram.Message) -> bool:
    if len(message.text) <= config.NAME_MAX_LEN:
        user.name = message.text
        return True
    return False


def collect_age(user: User, message: telegram.Message) -> bool:
    if len(message.text) == 2 and message.text.isdigit() and int(message.text) > config.min_user_age:
        user.age = int(message.text)
        return True
    return False


def collect_faculty(user: User, message: telegram.Message) -> bool:
    if message.text in config.faculties:
        user.faculty = message.text
        return True
    return False


def collect_year(user: User, message: telegram.Message) -> bool:
    if message.text in config.years:
        user.year = int(message.text)
        return True
    return False


def collect_description(user: User, message: telegram.Message) -> bool:
    if len(message.text) <= config.DESCRIPTION_MAX_LEN:
        user.description = message.text
        return True
    return False


async def collect_interest(user: User, message: telegram.Message) -> str:
    if message.text == config.stop_keyword:
        user.status = config.PHOTO
        return 'finish'
    elif len(message.text) <= config.INTEREST_MAX_LEN:
        result = user.add_interest(message.text.capitalize())
        if result == 'ok':
            return 'next'
        else:
            return result
    return 'wrong'


def collect_sex(user: User, message: telegram.Message) -> bool:
    if message.text in config.sexes:
        user.sex = config.sexes_dict[message.text]
        return True
    return False


def collect_sex_prefs(user: User, message: telegram.Message) -> bool:
    if message.text in config.sex_prefs:
        user.sex_preferences = config.sex_prefs_dict[message.text]
        return True
    return False


def collect_age_prefs(user: User, message: telegram.Message) -> bool:
    split = message.text.split(config.ages_split)
    if len(split) != 2:
        return False

    for number in split:
        if not number.strip().isdigit() and len(number.strip()) != 2:
            return False

    min_age = int(split[0])
    max_age = int(split[1])

    if max_age < min_age or min_age < config.min_user_age:
        return False

    user.min_age = min_age
    user.max_age = max_age
    return True


def get_years_keyboard():
    keyboard = copy.deepcopy(config.replies['year']['markup'])
    for i, year in enumerate(config.years):
        keyboard.add_callback(0, i, f'{config.edit_data_callback}:year:{year}')
    return keyboard.inline


def get_sexes_keyboard():
    keyboard = copy.deepcopy(config.replies['sex']['markup'])
    for i in range(len(config.sexes)):
        keyboard.add_callback(0, i, f'{config.edit_data_callback}:sex:{i}')
    return keyboard.inline


def get_sex_prefs_keyboard():
    keyboard = copy.deepcopy(config.replies['sex_preferences']['markup'])
    for i in range(len(config.sex_prefs)):
        keyboard.add_callback(0, i, f'{config.edit_data_callback}:sex_prefs:{i}')
    return keyboard.inline


def get_faculty_markup(user):
    faculty_markup = []

    for faculty in config.faculties[user.page * config.items_in_page:user.page * config.items_in_page + config.items_in_page]:
        faculty_markup.append([faculty])

    if user.page == 0:
        faculty_markup.append(['>>'])
    elif user.page == config.last_faculty_page - 1:
        faculty_markup.append(['<<'])
    else:
        faculty_markup.append(['<<', '>>'])

    markup = Markup(faculty_markup)
    for row_num, row in enumerate(faculty_markup[:-1]):
        for col_num, col in enumerate(row):
            markup.add_callback(row_num, col_num, f'{config.edit_data_callback}:faculty:{user.page}:{row_num}')

    if user.page == 0:
        markup.add_callback(len(faculty_markup) - 1, 0, f'{config.edit_data_callback}:faculty_page:1')
    elif user.page == config.last_faculty_page - 1:
        markup.add_callback(len(faculty_markup) - 1, 0, f'{config.edit_data_callback}:faculty_page:-1')
    else:
        markup.add_callback(len(faculty_markup) - 1, 0, f'{config.edit_data_callback}:faculty_page:-1')
        markup.add_callback(len(faculty_markup) - 1, 1, f'{config.edit_data_callback}:faculty_page:1')

    return markup.inline


def get_interests_markup(user):
    interests_markup = []

    non_user_interests = [i for i in config.interests if i not in user.get_interests_list()]

    if len(non_user_interests) % config.items_in_page == 0:
        last_page = len(non_user_interests) // config.items_in_page
    else:
        last_page = len(non_user_interests) // config.items_in_page + 1

    if user.page * config.items_in_page >= len(non_user_interests):
        user.page -= 1

    for interest in non_user_interests[user.page * config.items_in_page:user.page * config.items_in_page + config.items_in_page]:
        interests_markup.append([interest])

    with_transitions = False
    if config.items_in_page < len(non_user_interests):
        with_transitions = True

    if with_transitions:
        if user.page == 0:
            interests_markup.append(['>>'])
        elif user.page == last_page - 1:
            interests_markup.append(['<<'])
        else:
            interests_markup.append(['<<', '>>'])

    interests_markup.append([config.stop_keyword])

    markup = Markup(interests_markup)
    for row_num, row in enumerate(interests_markup[:-1]):
        for col_num, col in enumerate(row):
            markup.add_callback(row_num, col_num, f'{config.edit_data_callback}:interests:{user.page}:{row_num}')

    if with_transitions:
        if user.page == 0:
            markup.add_callback(len(interests_markup) - 2, 0, f'{config.edit_data_callback}:interests_page:1')
        elif user.page == last_page - 1:
            markup.add_callback(len(interests_markup) - 2, 0, f'{config.edit_data_callback}:interests_page:-1')
        else:
            markup.add_callback(len(interests_markup) - 2, 0, f'{config.edit_data_callback}:interests_page:-1')
            markup.add_callback(len(interests_markup) - 2, 1, f'{config.edit_data_callback}:interests_page:1')

    markup.add_callback(len(interests_markup) - 1, 0, f'{config.edit_data_callback}:interests:stop')

    return markup.inline


def get_nth_interest(user, n):
    user_interests = user.get_interests_list()

    i = 0
    for interest in config.interests:
        if interest not in user_interests:
            if i == n:
                return interest
            i += 1


async def bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.edited_message:
        return

    message = update.message
    with engine.connect() as conn:
        with User(mo, conn, message.from_user.id) as user:
            if user.ban_count >= config.max_ban_count:
                user.ban_timestamp = datetime.now() + config.ban_duration
                if await still_banned(user, context.bot):
                    return

            if user.status == config.NEW:
                if message.text == config.agreed_keyword:
                    user.status = config.NAME
                    user.username = message.from_user.name
                    await context.bot.edit_message_text(text=config.replies['terms']['text'],
                                                        chat_id=user.chat_id,
                                                        message_id=user.active_msg_id,
                                                        parse_mode=ParseMode.MARKDOWN_V2)
                    await send_reply(message, 'name')
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.NAME:
                if collect_name(user, message):
                    user.status = config.AGE
                    await send_reply(message, 'age')
                else:
                    await message.reply_text(config.get_wrong_len_reply(len(message.text), config.NAME_MAX_LEN))

            elif user.status == config.AGE:
                if collect_age(user, message):
                    faculty_msg = await message.reply_text(text=config.replies['faculty']['text'],
                                                           reply_markup=get_faculty_markup(user))
                    user.status = config.FACULTY
                    user.active_msg_id = faculty_msg.id
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.FACULTY:
                if collect_faculty(user, message):
                    await context.bot.edit_message_text(text=config.replies['after_faculty'].format(user.faculty),
                                                        chat_id=user.chat_id,
                                                        message_id=user.active_msg_id)
                    years_msg = await message.reply_text(text=config.replies['year']['text'],
                                                         reply_markup=get_years_keyboard())
                    user.status = config.YEAR
                    user.page = 0
                    user.active_msg_id = years_msg.id
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.YEAR:
                if collect_year(user, message):
                    user.status = config.DESCRIPTION
                    user.page = 0
                    await context.bot.edit_message_text(text=config.replies['after_year'].format(user.year),
                                                        chat_id=user.chat_id,
                                                        message_id=user.active_msg_id)
                    await send_reply(message, 'description')
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.DESCRIPTION:
                if collect_description(user, message):
                    interests_msg = await message.reply_text(text=config.get_interests_text(user, ''),
                                                             reply_markup=get_interests_markup(user))
                    user.status = config.INTERESTS
                    user.clear_interests()
                    user.active_msg_id = interests_msg.id
                else:
                    await message.reply_text(config.get_wrong_len_reply(len(message.text), config.NAME_MAX_LEN))

            elif user.status == config.INTERESTS:
                result = await collect_interest(user, message)
                if result == 'next':
                    await context.bot.edit_message_text(text=config.get_interests_text(user, ''),
                                                        chat_id=user.chat_id,
                                                        message_id=user.active_msg_id,
                                                        reply_markup=get_interests_markup(user))
                    return
                elif result == 'wrong':
                    await message.reply_text(config.get_wrong_len_reply(len(message.text), config.NAME_MAX_LEN))
                elif result == 'too_much':
                    await message.reply_text(config.replies['too_much_interests'])
                elif result == 'alreay_has':
                    await message.reply_text(config.replies['already_has_interest'])
                elif result == 'finish':
                    await context.bot.edit_message_text(text=config.get_interests_text(user, '', with_prompt=False),
                                                        chat_id=user.chat_id,
                                                        message_id=user.active_msg_id)
                    sexes_msg = await message.reply_text(text=config.replies['sex']['text'],
                                                         reply_markup=get_sexes_keyboard())
                    user.status = config.SEX
                    user.page = 0
                    user.active_msg_id = sexes_msg.id

            elif user.status == config.SEX:
                if collect_sex(user, message):
                    user.status = config.SEX_PREFERENCES

                    await context.bot.edit_message_text(text=config.replies['after_sex'].format(config.sexes[user.sex]),
                                                        chat_id=user.chat_id,
                                                        message_id=user.active_msg_id)
                    await message.reply_text(text=config.replies['sex_preferences']['text'],
                                             reply_markup=get_sex_prefs_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.SEX_PREFERENCES:
                if collect_sex_prefs(user, message):
                    user.status = config.AGE_PREFERENCES
                    user.active_msg_id = None

                    await send_reply(message, 'age_preferences')
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.AGE_PREFERENCES:
                if collect_age_prefs(user, message):
                    user.status = config.PHOTO
                    await send_reply(message, 'photo')
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.CONFIRMATION:
                await message.reply_text(config.replies['waiting_for_confirmation'])

            elif user.status == config.MAIN_MENU:
                if message.text == config.edit_profile_phrase:
                    edit_profile_msg = await message.reply_photo(caption=config.get_profile_caption(user),
                                                                 photo=base64.b64decode(user.photo.encode('ascii')),
                                                                 reply_markup=build_edit_profile_keyboard())
                    if user.active_msg_id is not None:
                        await context.bot.edit_message_reply_markup(chat_id=user.chat_id,
                                                                    message_id=user.active_msg_id,
                                                                    reply_markup=None)
                    user.active_msg_id = edit_profile_msg.id
                elif message.text == config.start_swiping_phrase:
                    if not user.visible:
                        await message.reply_text(config.replies['need_to_be_visible'])
                        return

                    profile_data = user.get_next_match()
                    if profile_data is not None:
                        profile_msg = await message.reply_photo(caption=config.get_profile_caption(profile_data, with_tg=False),
                                                                photo=base64.b64decode(profile_data.photo.encode('ascii')),
                                                                reply_markup=build_swipe_keyboard(profile_data))
                        if user.active_msg_id is not None:
                            await context.bot.edit_message_reply_markup(chat_id=user.chat_id,
                                                                        message_id=user.active_msg_id,
                                                                        reply_markup=None)
                        user.active_msg_id = profile_msg.id
                    else:
                        user.active_msg_id = None
                        await message.reply_text(config.replies['no_more_matches'])

            elif user.status == config.EDIT_NAME:
                if collect_name(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.get_wrong_len_reply(len(message.text), config.NAME_MAX_LEN))

            elif user.status == config.EDIT_AGE:
                if collect_age(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.EDIT_FACULTY:
                if collect_faculty(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])

            elif user.status == config.EDIT_YEAR:
                if collect_year(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])
                    
            elif user.status == config.EDIT_DESCRIPTION:
                if collect_description(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.get_wrong_len_reply(len(message.text), config.NAME_MAX_LEN))

            elif user.status == config.EDIT_INTERESTS:
                result = await collect_interest(user, message)
                if result == 'next':
                    return
                elif result == 'wrong':
                    await message.reply_text(config.get_wrong_len_reply(len(message.text), config.NAME_MAX_LEN))
                elif result == 'too_much':
                    await message.reply_text(config.replies['too_much_interests'])
                elif result == 'finish':
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                    
            elif user.status == config.EDIT_SEX:
                if collect_sex(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])
                    
            elif user.status == config.EDIT_SEX_PREFERENCES:
                if collect_sex_prefs(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])
                    
            elif user.status == config.EDIT_AGE_PREFERENCES:
                if collect_age_prefs(user, message):
                    user.status = config.MAIN_MENU
                    await context.bot.edit_message_caption(chat_id=user.chat_id,
                                                           message_id=user.active_msg_id,
                                                           caption=config.get_profile_caption(user),
                                                           reply_markup=build_edit_profile_keyboard())
                else:
                    await message.reply_text(config.replies['wrong_input'])


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    with engine.connect() as conn:
        with User(mo, conn, message.from_user.id) as user:
            if user.ban_count >= config.max_ban_count:
                user.ban_timestamp = datetime.now() + config.ban_duration
                if await still_banned(user, context.bot):
                    return

            if user.status == config.PHOTO:
                file = await context.bot.get_file(message.photo[-1].file_id)
                file = BytesIO(await file.download_as_bytearray())
                user.photo = base64.b64encode(file.getvalue()).decode()
                user.status = config.CONFIRMATION
                await send_reply(message, 'confirmation')
                
            elif user.status == config.CONFIRMATION:
                file = await context.bot.get_file(message.photo[-1].file_id)
                file = BytesIO(await file.download_as_bytearray())

                keyboard = copy.deepcopy(config.admin_approval_markup)
                keyboard.add_callback(0, 0, f'{config.positive_approval_callback}:{message.from_user.id}')
                keyboard.add_callback(0, 1, f'{config.negative_approval_callback}:{message.from_user.id}')

                media = [InputMediaPhoto(base64.b64decode(user.photo.encode('ascii')),
                                         caption=config.get_profile_caption(user)),
                         InputMediaPhoto(file.read())]

                await context.bot.send_media_group(chat_id=config.admin_group_chat_id,
                                                   media=media)

                await context.bot.send_message(text=f'{config.admin_approval_caption} ({message.from_user.name})',
                                               chat_id=config.admin_group_chat_id,
                                               reply_markup=keyboard.inline)
                
            elif user.status == config.EDIT_PHOTO:
                file = await context.bot.get_file(message.photo[-1].file_id)
                file = BytesIO(await file.download_as_bytearray())
                user.photo = base64.b64encode(file.getvalue()).decode()
                user.status = config.MAIN_MENU
                await message.reply_photo(caption=f'{config.get_profile_caption(user)}',
                                          reply_markup=build_edit_profile_keyboard(),
                                          photo=file.read())
            else:
                await message.reply_text(config.replies['unexpected_photo'])


async def image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(config.replies['image'])


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback = query.data.split(':', 1)[0]

    if callback == config.positive_approval_callback or \
            callback == config.negative_approval_callback or \
            callback == config.show_profile_callback:
        user_chat_id = query.data.split(':')[1]
        with engine.connect() as conn:
            with User(mo, conn, user_chat_id) as user:
                if callback == config.show_profile_callback:
                    detail = query.data.split(':')[2]
                    if detail == 'like':
                        await query.edit_message_reply_markup(None)
                        await context.bot.send_photo(chat_id=query.from_user.id,
                                                     caption=f'#like\n{config.get_profile_caption(user, with_tg=False)}',
                                                     reply_markup=build_like_reply_markup(user.chat_id),
                                                     photo=base64.b64decode(user.photo.encode('ascii')))

                    elif detail == 'match':
                        await query.edit_message_reply_markup(None)
                        await context.bot.send_photo(chat_id=query.from_user.id,
                                                     caption=f'#match\n{config.get_profile_caption(user)}',
                                                     photo=base64.b64decode(user.photo.encode('ascii')))

                elif callback == config.positive_approval_callback:
                    user.status = config.MAIN_MENU

                    await context.bot.send_message(chat_id=user.chat_id,
                                                   text=config.replies['positive_approval']['text'],
                                                   reply_markup=config.replies['positive_approval']['markup'])
                    await query.edit_message_caption(
                        f'{query.message.caption} ({config.approval_caption} by {query.from_user.name})')

                elif callback == config.negative_approval_callback:
                    user.ban_count += 1
                    await context.bot.send_message(chat_id=user.chat_id,
                                                   text=config.replies['negative_approval'])
                    await query.edit_message_caption(
                        f'{query.message.caption} ({config.disapproval_caption} by {query.from_user.name})')
    else:
        with engine.connect() as conn:
            with User(mo, conn, query.from_user.id) as user:
                if user.ban_count >= config.max_ban_count:
                    user.ban_timestamp = datetime.now() + config.ban_duration
                    if await still_banned(user, context.bot):
                        return

                if callback == config.swipe_callback:
                    passive_user_id, like_value, passive_user_chat_id = int(query.data.split(':')[1]), \
                                                                        int(query.data.split(':')[2]), \
                                                                        int(query.data.split(':')[3])
                    event = user.like(passive_user_id, like_value)

                    if event == 'like':
                        await context.bot.send_message(chat_id=passive_user_chat_id,
                                                       text=config.like_text,
                                                       reply_markup=build_like_markup(user))

                    elif event == 'match':
                        await context.bot.send_message(chat_id=passive_user_chat_id,
                                                       text=config.match_text,
                                                       reply_markup=build_match_markup(user.chat_id))

                        await context.bot.send_message(chat_id=user.chat_id,
                                                       text=config.match_text,
                                                       reply_markup=build_match_markup(passive_user_chat_id))

                    profile_data = user.get_next_match()
                    if profile_data is None:
                        user.active_msg_id = None
                        await query.delete_message()
                        await context.bot.send_message(user.chat_id, config.replies['no_more_matches'])
                        return

                    await query.edit_message_media(
                        InputMediaPhoto(base64.b64decode(profile_data.photo.encode('ascii'))))
                    await query.edit_message_caption(
                        caption=config.get_profile_caption(profile_data, with_tg=False),
                        reply_markup=build_swipe_keyboard(profile_data))

                elif callback == config.like_reply_callback:
                    passive_user_chat_id, detail = query.data.split(':')[1], query.data.split(':')[2]

                    await query.edit_message_reply_markup(None)
                    if detail == 'like':
                        with User(mo, conn, passive_user_chat_id) as passive_user:

                            await query.edit_message_caption(caption=config.get_profile_caption(passive_user),
                                                             reply_markup=None)

                            await context.bot.send_message(chat_id=passive_user.chat_id,
                                                           text=config.match_text,
                                                           reply_markup=build_match_markup(user.chat_id))

                elif callback == config.edit_data_callback:
                    detail = query.data.split(':', 1)[1]
                    if detail == 'confirmed':
                        user.status = config.NAME
                        user.username = query.from_user.name

                        await query.edit_message_text(f'{query.message.text}\n\nТы согласился.')
                        await context.bot.send_message(chat_id=user.chat_id,
                                                       text=config.replies['name']['text'])

                    elif detail.startswith('faculty_page:'):
                        user.page += int(detail.split(':')[1])
                        if user.status == config.EDIT_FACULTY:
                            await query.edit_message_reply_markup(reply_markup=get_faculty_markup(user))
                        else:
                            await query.edit_message_text(text=config.replies['faculty']['text'],
                                                          reply_markup=get_faculty_markup(user))

                    elif detail.startswith('faculty:'):
                        page_num, row_num = int(detail.split(':')[1]), int(detail.split(':')[2])
                        user.faculty = config.faculties[page_num * config.items_in_page + row_num]

                        if user.status == config.EDIT_FACULTY:
                            user.status = config.MAIN_MENU
                            user.page = 0

                            await query.edit_message_caption(caption=config.get_profile_caption(user),
                                                             reply_markup=build_edit_profile_keyboard())
                            return

                        user.status = config.YEAR
                        user.page = 0

                        await query.edit_message_text(config.replies["after_faculty"].format(user.faculty))
                        years_msg = await context.bot.send_message(chat_id=user.chat_id,
                                                                   text=config.replies['year']['text'],
                                                                   reply_markup=get_years_keyboard())
                        user.active_msg_id = years_msg.id

                    elif detail.startswith('year:'):
                        user.year = int(detail.split(':', 1)[1])

                        if user.status == config.EDIT_YEAR:
                            user.status = config.MAIN_MENU
                            await query.edit_message_caption(caption=config.get_profile_caption(user),
                                                             reply_markup=build_edit_profile_keyboard())
                            return

                        user.status = config.DESCRIPTION

                        await query.edit_message_text(config.replies["after_year"].format(user.year))
                        await context.bot.send_message(chat_id=user.chat_id,
                                                       text=config.replies['description']['text'])

                    elif detail.startswith('interests_page:'):
                        user.page += int(detail.split(':')[1])
                        if user.status == config.EDIT_INTERESTS:
                            await query.edit_message_reply_markup(reply_markup=get_interests_markup(user))
                        else:
                            await query.edit_message_text(text=config.get_interests_text(user, ''),
                                                          reply_markup=get_interests_markup(user))

                    elif detail.startswith('interests:'):
                        if detail.endswith('stop'):
                            if user.status == config.EDIT_INTERESTS:
                                user.status = config.MAIN_MENU
                                user.page = 0
                                await query.edit_message_caption(caption=config.get_profile_caption(user),
                                                                 reply_markup=build_edit_profile_keyboard())
                                return

                            await query.edit_message_text(text=config.get_interests_text(user, '', with_prompt=False))
                            sexes_msg = await context.bot.send_message(chat_id=user.chat_id,
                                                                       text=config.replies['sex']['text'],
                                                                       reply_markup=get_sexes_keyboard())

                            user.status = config.SEX
                            user.page = 0
                            user.active_msg_id = sexes_msg.id
                            return

                        page_num, row_num = int(detail.split(':')[1]), int(detail.split(':')[2])
                        interest = get_nth_interest(user, page_num * config.items_in_page + row_num)

                        result = user.add_interest(interest)

                        if user.status == config.EDIT_INTERESTS:
                            if result == 'ok':
                                await query.edit_message_caption(caption=f"{config.get_profile_caption(user)}\n\n"
                                                                         f"{config.get_interests_text(user, f'+ {interest}')}",
                                                                 reply_markup=get_interests_markup(user))
                            elif result == 'too_much':
                                await query.edit_message_caption(caption=f"{config.get_profile_caption(user)}\n\n"
                                                                         f"{config.get_interests_text(user, config.replies['too_much_interests'])}",
                                                                 reply_markup=get_interests_markup(user))
                            elif result == 'already_has':
                                await query.edit_message_caption(caption=f"{config.get_profile_caption(user)}\n\n"
                                                                         f"{config.get_interests_text(user, config.replies['already_has_interest'])}",
                                                                 reply_markup=get_interests_markup(user))
                            return

                        if result == 'ok':
                            await query.edit_message_text(text=config.get_interests_text(user, f'+ {interest}'),
                                                          reply_markup=get_interests_markup(user))
                        elif result == 'too_much':
                            await query.edit_message_text(text=config.get_interests_text(user, config.replies['too_much_interests']),
                                                          reply_markup=get_interests_markup(user))
                        elif result == 'already_has':
                            await query.edit_message_text(text=config.get_interests_text(user, config.replies['already_has_interest']),
                                                          reply_markup=get_interests_markup(user))

                    elif detail.startswith('sex:'):
                        user.sex = int(detail.split(':')[1])

                        if user.status == config.EDIT_SEX:
                            user.status = config.MAIN_MENU
                            await query.edit_message_caption(caption=config.get_profile_caption(user),
                                                             reply_markup=build_edit_profile_keyboard())
                            return

                        await query.edit_message_text(config.replies["after_sex"].format(config.sexes[user.sex]))
                        sex_prefs_msg = await context.bot.send_message(chat_id=user.chat_id,
                                                                       text=config.replies['sex_preferences']['text'],
                                                                       reply_markup=get_sex_prefs_keyboard())
                        user.active_msg_id = sex_prefs_msg.id

                    elif detail.startswith('sex_prefs:'):
                        user.sex_preferences = int(detail.split(':')[1])

                        if user.status == config.EDIT_SEX_PREFERENCES:
                            user.status = config.MAIN_MENU
                            await query.edit_message_caption(caption=config.get_profile_caption(user),
                                                             reply_markup=build_edit_profile_keyboard())
                            return

                        user.status = config.AGE_PREFERENCES
                        user.active_msg_id = None

                        await query.edit_message_text(config.replies["after_sex_prefs"].format(config.sex_prefs[user.sex_preferences]))
                        await context.bot.send_message(chat_id=user.chat_id,
                                                       text=config.replies['age_preferences']['text'])

                elif callback == config.edit_profile_callback:
                    detail = query.data.split(':')[1]
                    if detail == 'name':
                        user.status = config.EDIT_NAME
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=None)

                    elif detail == 'age':
                        user.status = config.EDIT_AGE
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=None)

                    elif detail == 'faculty':
                        user.status = config.EDIT_FACULTY
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=get_faculty_markup(user))

                    elif detail == 'year':
                        user.status = config.EDIT_YEAR

                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=get_years_keyboard())

                    elif detail == 'description':
                        user.status = config.EDIT_DESCRIPTION
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=None)

                    elif detail == 'interests':
                        user.status = config.EDIT_INTERESTS
                        user.clear_interests()
                        await query.edit_message_caption(
                            caption=f'{config.get_profile_caption(user)}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=get_interests_markup(user))
                        
                    elif detail == 'sex':
                        user.status = config.EDIT_SEX
                        await query.edit_message_caption(caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                                                         reply_markup=get_sexes_keyboard())
                        
                    elif detail == 'sex_preferences':
                        user.status = config.EDIT_SEX_PREFERENCES
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=get_sex_prefs_keyboard())
                        
                    elif detail == 'age_preferences':
                        user.status = config.EDIT_AGE_PREFERENCES
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=None)

                    elif detail == 'photo':
                        user.status = config.EDIT_PHOTO
                        await query.edit_message_caption(
                            caption=f'{query.message.caption}\n\n{config.edit_profile_phrases[detail]}',
                            reply_markup=None)

                    elif detail == 'visible':
                        if user.visible:
                            await query.message.reply_text(config.replies['now_invisible'])
                        else:
                            await query.message.reply_text(config.replies['now_visible'])

                        user.visible = not user.visible
                        await query.edit_message_caption(caption=config.get_profile_caption(user),
                                                         reply_markup=build_edit_profile_keyboard())
                        return


def await_db_initialization():
    print('awaiting database initialization')
    while True:
        try:
            engine.connect()
            print('database is up, continuing')
            break
        except:
            print('database is not up, waiting')
            time.sleep(1)


def run():
    await_db_initialization()

    if not inspect(engine).dialect.has_table(engine.connect(), 'users'):
        init_database()

    Table('users', mo, autoload_with=engine)
    Table('interests', mo, autoload_with=engine)
    Table('user_user', mo, autoload_with=engine)
    Table('users_interests', mo, autoload_with=engine)

    # init tg
    application = ApplicationBuilder().token(config.bot_token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.Chat(config.admin_group_chat_id), bot))
    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.Document.IMAGE, image))

    application.run_polling()
