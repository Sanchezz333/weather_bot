import telebot
from telebot import types
import json
import os
import redis
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]
api_url = "https://api.openweathermap.org/data/2.5/"

print(
    """
Start telegram bot...
Work with TOKEN: """,
    TOKEN,
)

bot = telebot.TeleBot(TOKEN)


MAIN_STATE = "main"
CITY_STATE = "city"
WEATHER_DATE_STATE = "weather_date_handler"

redis_url = os.environ.get("REDIS_URL")
if redis_url is None:
    try:
        data = json.load(open("db/data.json", "r", encoding="utf-8"))

    except FileNotFoundError:
        data = {
            "states": {},
            MAIN_STATE: {},
            CITY_STATE: {},
            WEATHER_DATE_STATE: {},
        }
else:
    redis_db = redis.from_url(redis_url)
    raw_data = redis_db.get("data")
    if raw_data is None:
        data = {
            "states": {},
            MAIN_STATE: {},
            CITY_STATE: {},
            WEATHER_DATE_STATE: {},
        }
    else:
        data = json.loads(raw_data)


def change_data(key, user_id, value):
    data[key][user_id] = value
    if redis_url is None:
        json.dump(
            data,
            open("db/data.json", "w", encoding="utf-8"),
            indent=2,
            ensure_ascii=False,
        )
    else:
        redis_db = redis.from_url(redis_url)
        redis_db.set("data", json.dumps(data))


@bot.message_handler(func=lambda message: True)
def dispatcher(message: types.Message):
    user_id = str(message.from_user.id)
    state = data["states"].get(user_id, MAIN_STATE)

    if state == MAIN_STATE:
        main_handler(message)
    elif state == CITY_STATE:
        city_handler(message)
    elif state == WEATHER_DATE_STATE:
        weather_date(message)


def main_handler(message: types.Message):
    user_id = str(message.from_user.id)

    if message.text == "/start":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Погода"))

        bot.send_message(
            user_id,
            "Этот бот умеет предсказывать погоду",
            reply_markup=markup,
        )
        change_data("states", user_id, MAIN_STATE)

    elif message.text == "Погода":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            *[types.KeyboardButton(button) for button in ["Москва", "Санкт Петербург"]]
        )
        bot.send_message(
            user_id,
            "А какой город? Выбери или введи название",
            reply_markup=markup,
        )
        change_data("states", user_id, CITY_STATE)

    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Погода"))
        bot.send_message(
            user_id,
            "Я тебя не понял",
            reply_markup=markup,
        )


def city_handler(message: types.Message):
    user_id = str(message.from_user.id)
    params = {"q": message.text, "appid": WEATHER_TOKEN, "units": "metric"}
    res = requests.get(api_url + "weather", params=params)
    print(res.url)
    print(res.status_code)
    if int(res.status_code) < 400:
        change_data(WEATHER_DATE_STATE, user_id, message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(*[types.KeyboardButton(button) for button in ["Сегодня", "Завтра"]])
        bot.send_message(
            user_id,
            "А какая дата? Выбери или введи в формате дд.мм",
            reply_markup=markup,
        )
        change_data("states", user_id, WEATHER_DATE_STATE)

    else:
        bot.reply_to(message, "Я тебя не понял")


def weather_date(message: types.Message):
    user_id = str(message.from_user.id)
    city = data[WEATHER_DATE_STATE][user_id]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Погода"))
    if message.text.lower() == "сегодня":
        params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric"}
        res = requests.get(api_url + "weather", params=params)
        weather_data = res.json()
        bot.send_message(
            user_id,
            f"""Сегдня в городе {city.capitalize()} {weather_data["main"]["temp"]} градусов
Ощущается как {weather_data["main"]["feels_like"]} градусов
Влажность {weather_data["main"]["humidity"]}%
Ветер {weather_data["wind"]["speed"]} м/с""",
            reply_markup=markup,
        )
        change_data("states", user_id, MAIN_STATE)

    elif message.text.lower() == "завтра":
        bot.send_message(
            user_id,
            "Не доделано",
            reply_markup=markup,
        )
        change_data("states", user_id, MAIN_STATE)

    elif message.text == "/back":
        bot.send_message(
            user_id,
            "Ооооокей. Поехали обратно.",
            reply_markup=markup,
        )
        change_data("states", user_id, MAIN_STATE)

    else:
        bot.reply_to(message, "Я тебя не понял")


if __name__ == "__main__":
    bot.infinity_polling()
