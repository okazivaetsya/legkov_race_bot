import json
import logging
import os
from logging.handlers import RotatingFileHandler

import requests
import telebot
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BOT_TOKEN = os.getenv('BOT_TOKEN')
MY_TELEGRAM_ID = os.getenv('MY_TELEGRAM_ID')
URL = 'https://api.reg.place/v1/events/uralhim-gonka-legkova/'
PARAMS = {
    'heats_stats': 'true',
    'races': 'true'
}
HEATS_STATUSES = {
    'ready': 'зарегистрирована',
    'created': 'новая',
    'cancelled': 'отменена',
    'transferred': 'передана другому участнику'
}
GENDERS = {
    'male': 'М',
    'female': 'Ж'
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
        return 'cлоты продаются по максимальной цене 3500 руб'
    if adult_heats_count > 300:
        return (
            f'2500 руб. До повышения цены осталось '
            f'{800 - adult_heats_count} слотов'
        )
    return (
        f'1500 руб. До повышения цены осталось '
        f'{300 - adult_heats_count} слотов'
    )


def preparing_race_info(json_data):
    """Вытаскиваем из json все необходимые данные о гонке"""
    race_name = json_data['name']
    heats_conts = json_data['heats_ready_count']
    distance30k_name = json_data['races'][0]['name']
    distance30k_ready_heats_count = json_data['races'][0]['heats_ready_count']
    distance20k_name = json_data['races'][1]['name']
    distance20k_ready_heats_count = json_data['races'][1]['heats_ready_count']
    distance10k_name = json_data['races'][2]['name']
    distance10k_ready_heats_count = json_data['races'][2]['heats_ready_count']
    distance_kids_name = json_data['races'][3]['name']
    distance_kids_ready_heats_count = json_data[
        'races'
    ][3]['heats_ready_count']
    adult_heats_count = (
        distance30k_ready_heats_count +
        distance30k_ready_heats_count +
        distance10k_ready_heats_count
    )

    return (
        f'Название гонки: {race_name}\n'
        f'Всего зарегистрировано: {heats_conts}\n'
        f'{distance30k_name}: {distance30k_ready_heats_count}\n'
        f'{distance20k_name}: {distance20k_ready_heats_count}\n'
        f'{distance10k_name}: {distance10k_ready_heats_count}\n'
        f'{distance_kids_name}: {distance_kids_ready_heats_count}\n'
        f'Стоимость участия: {get_price_static(adult_heats_count)}'
    )


def preparing_heat_info(json_data):
    """Вытаскиваем из json все необходимые данные об участнике"""
    id = json_data['heat']['id']
    first_name = json_data['heat']['name_first']
    last_name = json_data['heat']['name_last']
    middle_name = json_data['heat']['name_middle']
    birth_date = json_data['heat']['birth_date']
    gender = GENDERS[json_data['heat']['gender']]
    paid_at = json_data['heat']['paid_at'].split('T')[0]
    status = HEATS_STATUSES[json_data['heat']['status']]

    return (
        f'id: {id}\n'
        f'Статус: {status}\n'
        f'ФИО: {first_name} {last_name} {middle_name}\n'
        f'Дата рождения: {birth_date}\n'
        f'Пол: {gender}\n'
        f'Дата оплаты заявки: {paid_at}\n'
    )


@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f'Пользователь {message.from_user.id} нажал старт')
    try:
        response = requests.get(URL, params=PARAMS)
        logger.info('Получен ответ от API')
        if response.status_code == 200:
            json_data = json.loads(response.text)['event']
            text_message = preparing_race_info(json_data)
            bot.send_message(message.from_user.id, text_message)
        else:
            bot.send_message(
                message.from_user.id,
                f'Статус ответа сервера: {response.status_code}'
            )
        logger.critical(f'Статус ответа сервера: {response.status_code}')

    except Exception as error:
        error_message = f'Сбой в работе программы: {error}'
        bot.send_message(
            message.from_user.id,
            f'Сбой в работе программы: {error}'
        )
        logger.critical(error_message)


@bot.message_handler(content_types=['text'])
def get_heat_info(message):
    params = {
        'token': 'f307873c-7d5f-4eff-a792-fa77662ee826'
    }
    try:
        heat_number = int(message.text)
        heat_url = f'https://api.reg.place/v1/heats/{heat_number}'
        response = requests.get(heat_url, params=params)
        json_data = json.loads(response.text)
        text_message = preparing_heat_info(json_data)
        bot.send_message(message.from_user.id, text_message)

    except Exception as error:
        error_message = f'Сбой в работе программы: {error}'
        bot.send_message(
            message.from_user.id,
            f'Сбой в работе программы: {error}'
        )
        logger.critical(error_message)


bot.polling(none_stop=True, interval=0)
