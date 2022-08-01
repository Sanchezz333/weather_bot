import telebot
from telebot import types
import json

TOKEN = ""
with open("tbot") as tkn:
    TOKEN = tkn.readline().strip()

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


try:
    data = json.load(open("db/data.json", "r", encoding="utf-8"))

except FileNotFoundError:
    data = {
        "states": {},
        MAIN_STATE: {},
        CITY_STATE: {},
        WEATHER_DATE_STATE: {},
    }


def change_data(key, user_id, value):
    data[key][user_id] = value
    json.dump(
        data,
        open("db/data.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False,
    )


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
        markup.add(*[types.KeyboardButton(button) for button in ["Мск", "СПб"]])
        bot.send_message(
            user_id,
            "А какой город?",
            reply_markup=markup,
        )
        change_data("states", user_id, CITY_STATE)

    else:
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            user_id,
            "Я тебя не понял",
            reply_markup=markup,
        )


def city_handler(message: types.Message):
    user_id = str(message.from_user.id)

    if message.text.lower() in ["мск", "спб"]:
        change_data(WEATHER_DATE_STATE, user_id, message.text.lower())
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(*[types.KeyboardButton(button) for button in ["сегодня", "завтра"]])
        bot.send_message(
            user_id,
            'А какая дата? Введи "сегодня" или "завтра"',
            reply_markup=markup,
        )
        change_data("states", user_id, WEATHER_DATE_STATE)

    else:
        bot.reply_to(message, "Я тебя не понял")


WEATHER = {
    "спб": {
        "сегодня": "27",
        "завтра": "32",
    },
    "мск": {
        "сегодня": "23",
        "завтра": "24",
    },
}


def weather_date(message: types.Message):
    user_id = str(message.from_user.id)
    city = data[WEATHER_DATE_STATE][user_id]

    if message.text.lower() == "сегодня":
        bot.send_message(user_id, WEATHER[city][message.text.lower()])
        change_data("states", user_id, MAIN_STATE)

    elif message.text.lower() == "завтра":
        bot.send_message(user_id, WEATHER[city][message.text.lower()])
        change_data("states", user_id, MAIN_STATE)

    elif message.text == "/back":
        bot.send_message(user_id, "Ооооокей. Поехали обратно.")
        change_data("states", user_id, MAIN_STATE)

    else:
        bot.reply_to(message, "Я тебя не понял")


if __name__ == "__main__":
    bot.infinity_polling()
