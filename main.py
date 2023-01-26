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
REGPLACE_TOKEN = os.getenv('REGPLACE_TOKEN')
URL = 'https://api.reg.place/v1/events/uralhim-gonka-legkova/'
PARAMS = {
    'heats_stats': 'true',
    'races': 'true'
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
        distance20k_ready_heats_count +
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
    id = json_data['heat']['id']
    first_name = json_data['heat']['name_first']
    last_name = json_data['heat']['name_last']
    middle_name = json_data['heat']['name_middle']
    birth_date = json_data['heat']['birth_date']
    gender = GENDERS[json_data['heat']['gender']]
    status = HEATS_STATUSES[json_data['heat']['status']]
    if status == 'зарегистрирована':
        paid_at = json_data['heat']['paid_at'].split('T')[0]
    else:
        paid_at = None

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
    """Обработчик команды start"""
    logger.info(f'Пользователь {message.from_user.id} нажал старт')
    try:
        response = requests.get(URL, params=PARAMS)
        logger.info('Получен ответ от API')
        if response.status_code == 200:
            json_data = json.loads(response.text)['event']
            text_message = preparing_race_info(json_data)
            bot.send_message(message.from_user.id, text_message)
    except Exception as error:
        error_message = f'Сбой в работе программы: {error}'
        bot.send_message(
            message.from_user.id,
            f'Сбой в работе программы: {error}'
        )
        logger.critical(error_message)


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
    homework_list = response['homeworks']
    return homework_list


@bot.message_handler(content_types=['text'])
def get_heat_info(message):
    """Обработчик тестовых сообщений"""
    params = {
        'token': REGPLACE_TOKEN
    }
    try:
        heat_number = int(message.text)
        heat_url = f'https://api.reg.place/v1/heats/{heat_number}'
        response = requests.get(heat_url, params=params)
        if response.status_code == 200:
            json_data = json.loads(response.text)
            text_message = preparing_heat_info(json_data)
            bot.send_message(message.from_user.id, text_message)
        else:
            bot.send_message(
                    message.from_user.id,
                    f'Ошибка: Статус ответа сервера: {response.status_code}'
                )
            logger.critical(f'Статус ответа сервера: {response.status_code}')

    except Exception as error:
        error_message = f'Сбой в работе программы: {error}'
        bot.send_message(
            message.from_user.id,
            f'Сбой в работе программы: {error}'
        )
        logger.critical(error_message)


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


def main():
    logger.info('Функция main() запущена')
    if not check_tokens():
        quit()
    bot.polling(none_stop=True, interval=0)


if __name__ == '__main__':
    main()
