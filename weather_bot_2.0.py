import telebot
from telebot import types
import json
import os
import requests
from datetime import date, timedelta, datetime, time
import copy
import random
import sys

TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]
TARGET_ID = os.environ["TARGET_ID"]
api_url = "https://api.openweathermap.org/data/2.5/"

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

eprint(
    """
Start telegram bot...
Work with TOKEN: """,
    TOKEN,
)

bot = telebot.TeleBot(TOKEN)

user_tmp = {
    'status': 'main',
    'city': None,
    'user_cities': [],
    'raw_state': False,
}
security_code = None

try:
    data = json.load(open("/data/data.json", "r", encoding="utf-8"))

except FileNotFoundError:
    data = {}


def new_user():
    return copy.deepcopy(user_tmp)

def get_value(user, key):
    value = user.get(key, '*%*')
    if value == '*%*':
        patcher(user, key)
    return user[key]

def patcher(user, key):
    user[key] = copy.deepcopy(user_tmp[key])

def change_data():
    json.dump(
        data,
        open("/data/data.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False,
    )

def list_of_days():
    today = date.today()
    one_day = timedelta(days=1)
    day = today + one_day
    keys = []
    for i in range(3):
        day += one_day
        keys.append(day.strftime('%d-%m-%Y'))
    return keys

def weather_template(data):
    return f"""{data["weather"][0]["main"]}: {data["weather"][0]["description"]}
Температура {data['main']['temp']} градусов
Ощущается как {data["main"]["feels_like"]} градусов
Влажность {data["main"]["humidity"]}%
Ветер {data["wind"]["speed"]} м/с"""

def get_weather_text(weather_data, city, day):
    text = f"В городе {city} на {day.strftime('%d-%m-%Y')}:\n"
    for i in weather_data['list']:
        if day.strftime('%Y-%m-%d') in i['dt_txt']:
            if raw:
                text += f"""В {datetime.utcfromtimestamp(i['dt']).strftime('%H:%M')}
{json.dumps(weather_data, indent=4)}\n\n"""

            else:
                text += f"""В {datetime.utcfromtimestamp(i['dt']).strftime('%H:%M')}
Погода: {weather_template(i)}
\n"""

    return text

def send_code(user):
    user['status'] = 'get_code'
    global security_code
    security_code = int(random.random() * 1000000)
    eprint(f"Security code is: {security_code}")
    bot.send_message(
        TARGET_ID,
        str(security_code),
    )
    change_data()

def set_raw(user):
    raw = get_value(user, 'raw_state')
    user['raw_state'] = not(raw)


def send_data(user, message):
    user['status'] = 'main'
    if message.text == str(security_code):
        with open('/data/data.json', 'rb') as file:
            bot.send_document(user['id'], file)
    else:
        bot.send_message(
            user['id'],
            f"Пошел нахер! '{message.text}' != '{str(security_code)}'",
        )
    change_data()

def main_handler(user, message: types.Message):
    if message.text == "/start":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Погода"))

        bot.send_message(
            user['id'],
            "Этот бот умеет предсказывать погоду",
            reply_markup=markup,
        )
        user['status'] = 'main'
        change_data()

    elif message.text == "/add":
        bot.send_message(
            user['id'],
            "Введи город который хочешь добавить",            
        )
        user['status'] = 'add_city'
        change_data()

    elif message.text == "/del":
        bot.send_message(
            user['id'],
            "Введи город который хочешь удалить",
        )
        user['status'] = 'del_city'
        change_data()

    elif message.text == "Погода":
        cities = ["Москва", "Санкт Петербург"]
        cities += user['user_cities']
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            *[types.KeyboardButton(button) for button in cities]
        )
        bot.send_message(
            user['id'],
            "А какой город? Выбери или введи название",
            reply_markup=markup,
        )
        user['status'] = 'city'
        change_data()

    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Погода"))
        bot.send_message(
            user['id'],
            "Я тебя не понял",
            reply_markup=markup,
        )

def city_handler(user, message: types.Message):
    city = message.text
    params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric"}
    res = requests.get(api_url + "weather", params=params)
    if int(res.status_code) < 400:
        buttons = ["Сейчас", "Сегодня", "Завтра"] + list_of_days()

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(*[types.KeyboardButton(button) for button in buttons])
        bot.send_message(
            user['id'],
            "А какая дата?",
            reply_markup=markup,
        )
        user['city'] = city
        user['status'] = 'weather_date_handler'
        change_data()

    else:
        bot.reply_to(message, f"Города {city} не обнаружено")

def weather_date(user, message: types.Message):
    city = user['city']
    raw = get_value(user, 'raw_state')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Погода"))
    days = ["сегодня", "завтра"] + list_of_days()
    if message.text.lower() == "сейчас":
        params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric"}
        res = requests.get(api_url + "weather", params=params)
        weather_data = res.json()
        if raw:
            bot.send_message(
                user['id'],
                json.dumps(weather_data, indent=4),
                reply_markup = markup,
            )

        else:
            bot.send_message(
                user['id'],
                f"""Сейчас в городе {city} {weather_template(weather_data)}""",
                reply_markup=markup,
            )
        user['status'] = 'main'
        change_data()

    elif message.text.lower() in days:
        params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric"}
        res = requests.get(api_url + "forecast", params=params)
        weather_data = res.json()
        number_of_day = days.index(message.text.lower())
        day = date.today() + timedelta(days=number_of_day)

        bot.send_message(
            user['id'],
            get_weather_text(weather_data, city, day),
            reply_markup=markup,
        )
        user['status'] = 'main'
        change_data()

    elif message.text == "/back":
        bot.send_message(
            user['id'],
            "Ооооокей. Поехали обратно.",
            reply_markup=markup,
        )
        user['status'] = 'main'
        change_data()

    else:
        bot.reply_to(message, "Я тебя не понял")

def add_city(user, message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Погода"))

    if message.text == "/back":
        bot.send_message(
            user['id'],
            "Ооооокей. Поехали обратно.",
            reply_markup=markup,
        )
        user['status'] = 'main'
        change_data()
        
    else:
        city = message.text
        params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric"}
        res = requests.get(api_url + "weather", params=params)    
        if int(res.status_code) < 400:
            bot.send_message(
                user['id'],
                "Добавил!",
                reply_markup=markup,
            )
            user['user_cities'].append(city)
            user['status'] = 'main'
            change_data()

        else:
            bot.send_message(
                user['id'],
                "Нет такого города!",
            )

def del_city(user, message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Погода"))

    if message.text == "/back":
        bot.send_message(
            user['id'],
            "Ооооокей. Поехали обратно.",
            reply_markup=markup,
        )

    else:
        city = message.text
        if city in user['user_cities']:
            user['user_cities'].remove(city)
            bot.send_message(
                user['id'],
                "Убрал!",
                reply_markup=markup,
            )

        else:
            bot.send_message(
                user['id'],
                "Его и не было.",
                reply_markup=markup,
            )
        user['status'] = 'main'
        change_data()


METHODS = {
    'get_code': send_data,
    'main': main_handler,
    'city': city_handler,
    'weather_date_handler': weather_date,
    'add_city': add_city,
    'del_city': del_city,
}
@bot.message_handler(func=lambda message: True)
def dispatcher(message: types.Message):
    user_id = str(message.from_user.id)
    user = data.get(user_id, 'No user')
    if user == 'No user':
        user = new_user()
        user['id'] = user_id
        data[user_id] = user

    if message.text == "/get_data":
        send_code(user)
    elif message.text == "/raw":
        set_raw(user)
    else:
        METHODS.get(user['status'], main_handler)(user, message)


if __name__ == "__main__":
    bot.infinity_polling()
