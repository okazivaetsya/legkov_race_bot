import json
import logging
import os
from logging.handlers import RotatingFileHandler

import requests
import telebot
from telebot import types
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BOT_TOKEN = os.getenv('BOT_TOKEN')
MY_TELEGRAM_ID = os.getenv('MY_TELEGRAM_ID')
REGPLACE_TOKEN = os.getenv('REGPLACE_TOKEN')
URL = 'https://api.reg.place/v1/events/uralhim-gonka-legkova/'
PARAMS = {
    'heats_stats': 'true',
    'races': 'true',
    'compact': 'false'
}
HEATS_STATUSES = {
    'ready': 'зарегистрирована',
    'created': 'новая',
    'cancelled': 'отменена',
    'transferred': 'передана другому участнику',
    'locked': 'оплачивается'
}
GENDERS = {
    'male': 'М',
    'female': 'Ж'
}

RACES = {
    '70f36b3e-07f7-4ead-9c70-20bd95292bad': '30 км (мужчины)',
    '79c3e3b0-fa3e-46d4-8ac1-81929833ec09': '20 км (женщины)',
    'e277f22f-bb2f-449e-b319-5623c6fc1dff': '10 км (мужчины и женщины)',
    '71da9a7a-2699-42fc-a6a9-7a4171ae5879': 'Детская гонка 1 км, 3 км, 5 км',
}

bot = telebot.TeleBot(BOT_TOKEN)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'main_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def get_response_from_regplace():
    """Получаем данные от API reg.place"""
    response = requests.get(URL, params=PARAMS)
    json_data = json.loads(response.text)
    return json_data['event']


def get_price_static(adult_heats_count):
    """Определяем кол-во слотов до повышения цены"""
    if adult_heats_count > 800:
        return 'это максимальная цена!'
    if adult_heats_count > 300:
        return (
            f'до повышения цены осталось '
            f'{800 - adult_heats_count} слотов'
        )
    return (
        f'до повышения цены осталось '
        f'{300 - adult_heats_count} слотов'
    )


def preparing_race_info(json_data):
    """Вытаскиваем из json все необходимые данные о гонке"""
    race_name = json_data['name']
    heats_conts = json_data['heats_ready_count']
    distance30k_name = json_data['races'][0]['name']
    distance30k_ready_heats_count = json_data['races'][0]['heats_ready_count']
    distance30k_fee = json_data['races'][0]['fee']['base_amount']
    distance20k_name = json_data['races'][1]['name']
    distance20k_ready_heats_count = json_data['races'][1]['heats_ready_count']
    distance20k_fee = json_data['races'][1]['fee']['base_amount']
    distance10k_name = json_data['races'][2]['name']
    distance10k_ready_heats_count = json_data['races'][2]['heats_ready_count']
    distance10k_fee = json_data['races'][2]['fee']['base_amount']
    distance_kids_name = json_data['races'][3]['name']
    distance_kids_ready_heats_count = json_data[
        'races'
    ][3]['heats_ready_count']
    adult_heats_count = (
        distance30k_ready_heats_count +
        distance20k_ready_heats_count +
        distance10k_ready_heats_count
    )
    if distance30k_fee == distance20k_fee == distance10k_fee:
        price = distance30k_fee
    else:
        logger.critical(
                    f'Ошибка стоимости участия!!!\n'
                    f'30 км - {distance30k_fee}\n'
                    f'20 км - {distance20k_fee}\n'
                    f'10 км - {distance10k_fee}\n'
                )
        price = 'ОШИБКА!!! Цены кривые!'

    return (
        f'Название гонки: {race_name}\n'
        f'Всего зарегистрировано: {heats_conts}\n'
        f'{distance30k_name}: {distance30k_ready_heats_count}\n'
        f'{distance20k_name}: {distance20k_ready_heats_count}\n'
        f'{distance10k_name}: {distance10k_ready_heats_count}\n'
        f'{distance_kids_name}: {distance_kids_ready_heats_count}\n'
        f'Стоимость участия: {int(price)} руб. '
        f'({get_price_static(adult_heats_count)})'
    )


def get_adult_heats_count(json_data):
    """Получаем сумму всех зареганых взрослых заявок"""
    distance30k_ready_heats_count = json_data['races'][0]['heats_ready_count']
    distance20k_ready_heats_count = json_data['races'][1]['heats_ready_count']
    distance10k_ready_heats_count = json_data['races'][2]['heats_ready_count']
    return (
        distance30k_ready_heats_count +
        distance20k_ready_heats_count +
        distance10k_ready_heats_count
    )


def preparing_heat_info(json_data):
    """Вытаскиваем из json все необходимые данные об участнике"""
    id = json_data['data']['attributes']['number']
    first_name = json_data['data']['attributes']['name_first']
    last_name = json_data['data']['attributes']['name_last']
    middle_name = json_data['data']['attributes']['name_middle']
    birth_date = json_data['data']['attributes']['birth_date']
    gender = GENDERS[json_data['data']['attributes']['gender']]
    status = HEATS_STATUSES[json_data['data']['attributes']['status']]
    bib = json_data['data']['attributes']['bib']
    paid_at = json_data['data']['attributes']['paid_at']
    if paid_at is not None:
        paid_at = json_data['data']['attributes']['paid_at'].split('T')[0]
    dist = RACES[json_data['data']['relationships']['race']['data']['id']]
    return (
        f'id: {id}\n'
        f'Статус: {status}\n'
        f'Дистанция: {dist}\n'
        f'ФИО: {last_name} {first_name} {middle_name}\n'
        f'Дата рождения: {birth_date}\n'
        f'Пол: {gender}\n'
        f'Дата оплаты заявки: {paid_at}\n'
        f'Стартовый номер: {bib}\n'
    )


def check_tokens():
    """Проверка наличия токенов в окружении."""
    if not BOT_TOKEN:
        logger.critical(
            'В окружении отсутствует токен телеграм бота'
        )
        return False
    if not MY_TELEGRAM_ID:
        logger.critical(
            'В окружении отсутствует ID чата для персонального сообщения'
        )
        return False

    if not REGPLACE_TOKEN:
        logger.critical('В окружении отсутствует токен reg.place')
        return False
    return True


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        error_message = 'Ответ API не является словарем'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'event' or 'heat' not in response:
        error_message = 'Ответ API не содержит ключ "homeworks"'
        logger.error(error_message)
        raise KeyError(error_message)
    return response['homeworks']


@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды start"""
    logger.info(f'Пользователь {message.from_user.id} нажал старт')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Race statistic')
    btn2 = types.KeyboardButton('Athlete info')
    markup.add(btn1, btn2)
    try:
        response = requests.get(URL, params=PARAMS)
        logger.info('Получен ответ от API')
        if response.status_code == 200:
            json_data = json.loads(response.text)['event']
            text_message = preparing_race_info(json_data)
            bot.send_message(
                message.from_user.id,
                text_message,
                reply_markup=markup
            )
    except Exception as error:
        error_message = f'Сбой в работе программы: {error}'
        bot.send_message(
            message.from_user.id,
            f'Сбой в работе программы: {error}'
        )
        logger.critical(error_message)


@bot.message_handler(content_types=['text'])
def get_heat_info(message):
    """Обработчик тестовых сообщений"""
    params = {
        'token': REGPLACE_TOKEN
    }
    if message.text == 'Race statistic':
        start(message)
    elif message.text == 'Athlete info':
        text_message = 'Введите шестизначный номер заявки участника:'
        bot.send_message(message.from_user.id, text_message)
    else:
        try:
            heat_number = int(message.text)
            heat_url = f'https://api.reg.place/v1/heats/{heat_number}'
            response = requests.get(heat_url, params=params)
            if response.status_code == 200:
                uuid = json.loads(
                    response.text
                )['heat']['heat_url'].split('/')[-1]
                response = requests.get(
                    f'https://api.reg.place/v3/heats/{uuid}'
                )
                json_data = json.loads(response.text)
                text_message = preparing_heat_info(json_data)
                bot.send_message(message.from_user.id, text_message)
            else:
                bot.send_message(
                        message.from_user.id,
                        f'Ошибка!!! Статус ответа: {response.status_code}'
                    )
                logger.critical(
                    f'Статус ответа сервера: {response.status_code}'
                )

        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            bot.send_message(
                message.from_user.id,
                f'Сбой в работе программы: {error}'
            )
            logger.critical(error_message)


def main():
    logger.info('Функция main() запущена')
    if not check_tokens():
        quit()
    keyboard1 = telebot.types.ReplyKeyboardMarkup()
    keyboard1.row('Race statistic', 'Athlete info')
    bot.polling(none_stop=True, interval=0)


if __name__ == '__main__':
    main()
