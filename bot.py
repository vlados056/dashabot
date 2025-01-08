from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram import F
import asyncio
from pymongo import MongoClient
import datetime
import time
import hmac
import hashlib
import json
from aiohttp import web

# Токен вашего бота
API_TOKEN = "7643886458:AAGr6E4H3HlkkU7jSZncXUGP8e_t-O04RNc"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Подключение к базе данных MongoDB
uri = "mongodb+srv://mvstarcorp:UFnERtzkd9fwvqzm@cluster0.ihw7m.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
client = MongoClient(uri)
database = client.get_database("Yoga_bot")
clients_collection = database.get_collection("clients")

# ID канала
CHANNEL_ID = "2266785442"

# Ссылки на изображения
IMAGES = {
    "main": "https://imgur.com/q7Fgkhh",
    "group_practice": "https://imgur.com/5WWAIIc",
    "individual_practice": "https://imgur.com/EAXcUvg",
    "trial_practice": "https://imgur.com/ls7d2Ua",
    "results": "https://imgur.com/Rd4o7X4",
    "feedback": "https://imgur.com/HuPLLJ2",
    "tariff": "https://imgur.com/1PU75Nz",
}

# Дополнительные фотографии для результатов и отзывов
ADDITIONAL_PHOTOS = [
    "https://imgur.com/Gx6JnPF",
    "https://imgur.com/yTU7d3w",
    "https://imgur.com/kTfWNM3",
    "https://imgur.com/9kQ7axR",
    "https://imgur.com/JrYfCgH"
]

# Меню для результатов и отзывов
def results_menu_markup():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")],
        [InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]
    ])

# Главное меню
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ГРУППОВЫЕ ПРАКТИКИ", callback_data="group_practice")],
        [InlineKeyboardButton(text="ИНДИВИДУАЛЬНЫЕ ПРАКТИКИ", callback_data="individual_practice")],
        [InlineKeyboardButton(text="ПРОБНАЯ ПРАКТИКА", callback_data="trial_practice")],
        [InlineKeyboardButton(text="РЕЗУЛЬТАТЫ И ОТЗЫВЫ", callback_data="results")],
        [InlineKeyboardButton(text="ОБРАТНАЯ СВЯЗЬ", callback_data="feedback")]
    ])

# Функция занесения клиентов в базу данных
def add_client_to_db(user_id, user_name, subscription_status):
    if not clients_collection.find_one({'user_id': user_id}):
        clients_collection.insert_one({
            'user_id': user_id,
            'user_name': user_name,
            'subscription_status': subscription_status,
            'subscription_end_date': None,
            'last_reminder': None,
            'date_auth': datetime.datetime.now(datetime.UTC)
        })

# Функция обработки покупки
def process_purchase(client_id, subscription_duration):
    end_date = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=subscription_duration)
    clients_collection.update_one(
        {'user_id': client_id},
        {'$set': {'subscription_status': 'subscribed', 'subscription_end_date': end_date}}
    )
    add_user_to_channel(client_id)

# Функция добавления пользователя в канал
async def add_user_to_channel(client_id):
    try:
        await bot.add_chat_members(chat_id=CHANNEL_ID, user_id=client_id)
    except Exception as e:
        print(f"Ошибка при добавлении пользователя в канал: {e}")

# Функция проверки подписки
def check_subscriptions():
    for client in clients_collection.find():
        if client['subscription_status'] == 'subscribed':
            end_date = client['subscription_end_date']
            if end_date <= datetime.datetime.now(datetime.UTC):
                clients_collection.update_one(
                    {'user_id': client['user_id']},
                    {'$set': {'subscription_status': 'no_subscription', 'subscription_end_date': None}}
                )
                send_message(client['user_id'], "Привет! 😊\nВаша подписка завершилась, и доступ к нашим функциям временно ограничен.\nНо это легко исправить! Продлите подписку прямо сейчас и продолжайте практиковать и становиться лучше.\n\nЕсли у тебя остались вопросы или нужна помощь, пиши в личные сообщения — всегда на связи! 😊", main_menu())
                remove_user_from_channel(client['user_id'])
            elif end_date <= datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1):
                send_message(client['user_id'], "Привет! 😊\nНапоминаю, что завтра заканчивается срок вашей подписки. Чтобы не потерять доступ ко всем возможностям, продлите её заранее!\n\nЕсли у тебя есть вопросы, напиши мне — всегда рад помочь!", main_menu())

# Функция удаления пользователя из канала
async def remove_user_from_channel(client_id):
    try:
        await bot.kick_chat_member(chat_id=CHANNEL_ID, user_id=client_id)
    except Exception as e:
        print(f"Ошибка при удалении пользователя из канала: {e}")

# Функция отправки напоминаний
async def send_reminder(user_id):
    await send_message(user_id, "Привет! 😊\nЯ заметила, что вы интересовались практиками, но ещё не приобрели подписку. Если у вас остались вопросы или нужна дополнительная информация, всегда можете написать мне в личные сообщения @dariakobrina — я с радостью помогу!\n\nНе забудьте, что подписка открывает доступ к:\n✨ Практикам FYSM йоги в прямом эфире,\n✨ К записям практик - занимайся в любое удобное время,\n✨ К группе единомышленников, с которыми интереснее заниматься и кто всегда поддержит если лень вставать на коврик.\n\nНе откладывайте своё прекрасное состояние на потом, сделайте глубокий вдох, выдох и приходите ко мне на практику🤍", main_menu())

# Функция отправки сообщений
async def send_message(user_id, message, reply_markup=None):
    await bot.send_message(chat_id=user_id, text=message)

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    client_id = message.from_user.id
    user_name = message.from_user.full_name
    add_client_to_db(client_id, user_name, 'no_subscription')
    await message.answer_photo(
        IMAGES["main"],
        caption="Привет! \n\nМеня зовут Даша, я тренер по йоге с опытом более 4 лет. Если ты устал от болей в спине, стресса на работе или недостатка энергии, ты пришел по адресу!\n\nЯ помогу тебе:\n✨ Избавиться от болей в теле и улучшить осанку\n✨ Оберечь внутренний баланс и спокойствие\n✨ Поднять уровень энергии и снять стресс, даже если у тебя очень плотный график.\n\nВ этом боте ты можешь узнать все о моих занятиях, тарифах и условиях. Готов улучшить свое тело и настроение? Давай начнем прямо сейчас!\n\nВыбери, что тебе интересно и давай сделаем первый шаг к здоровью!",
        reply_markup=main_menu()
    )
    # Запуск задачи для отправки сообщения через 5 минут
    asyncio.create_task(send_delayed_message(client_id, message.chat.id))

# Функция для отправки сообщения через 5 минут
async def send_delayed_message(user_id, chat_id):
    await asyncio.sleep(120)  # 5 минут = 300 секунд
    await send_message(user_id, "Привет! 😊\nЯ заметила, что вы интересовались практиками, но ещё не приобрели подписку. Если у вас остались вопросы или нужна дополнительная информация, всегда можете написать мне в личные сообщения @dariakobrina — я с радостью помогу!\n\nНе забудьте, что подписка открывает доступ к:\n✨ Практикам FYSM йоги в прямом эфире,\n✨ К записям практик - занимайся в любое удобное время,\n✨ К группе единомышленников, с которыми интереснее заниматься и кто всегда поддержит если лень вставать на коврик.\n\nНе откладывайте своё прекрасное состояние на потом, сделайте глубокий вдох, выдох и приходите ко мне на практику🤍", main_menu())

# Обработчик кнопки "ГРУППОВЫЕ ПРАКТИКИ"
@dp.callback_query(F.data == "group_practice")
async def group_practice_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["group_practice"], caption="🫂Групповые практики\n\n✨ Практики в прямых эфирах 2 раза в неделю. ВТОРНИК, ПЯТНИЦА 8.00 МСК\n\n✨ Средняя продолжительность практики - 60 минут.\n\n✨ После каждого занятия запись сохраняется в канале. Тренируйтесь в любое удобное время, выбирая продолжительность и интенсивность, которая подходит именно вам.\n\n✨ Практики на канале идут от легких к сложным, поэтому можно спокойно начинать заниматься даже если у вас нет опыта в йоге."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ТАРИФ И ОПЛАТА", callback_data="tariff_group")],
            [InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "ИНДИВИДУАЛЬНЫЕ ПРАКТИКИ"
@dp.callback_query(F.data == "individual_practice")
async def individual_practice_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["individual_practice"], caption="🧘🧘🏻‍♀️Индивидуальные практики\n\n- Время и количество занятий подбирается индивидуально под ваше расписание.\n- Длительность: от 60 минут\n- Программа тренировочного процесса составляется индивидуально под ваш запрос и конкретное исходное состояние. За счет этого и происходит такой быстрый рост в практике.\n\n🌞Уже через 1-3 месяца регулярных практик вы почувствуете:\n- Спокойствие и более ясный ум в повседневной жизни.\n- Улучшение общего самочувствия, уменьшение дискомфорта в спине и суставах.\n- Легче справляться с рабочими и личными задачами, быстрее принимать решения."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ТАРИФ И ОПЛАТА", callback_data="tariff_individual")],
            [InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "ПРОБНАЯ ПРАКТИКА"
@dp.callback_query(F.data == "trial_practice")
async def trial_practice_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["trial_practice"], caption="Попробовав, ты ничего не теряешь, а только приобретаешь возможность изменить свою жизнь.\n\nПосле пробной практики напиши мне о своих ощущениях @dariakobrina.\n\nБуду тебе благодарна🤍"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ПОЛУЧИТЬ ПРОБНУЮ ПРАКТИКУ", url="https://youtu.be/ej-qJBF3jCQ?si=jMRDHDRvSrUZxfod")],
            [InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "РЕЗУЛЬТАТЫ И ОТЗЫВЫ"
@dp.callback_query(F.data == "results")
async def results_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["results"], caption="Результаты и отзывы моих учеников."),
        reply_markup=results_menu_markup()
    )
    # Отправка дополнительных фотографий
    for photo in ADDITIONAL_PHOTOS:
        await callback_query.message.answer_photo(photo=photo)
    # Отправка меню с фотографией после всех фотографий
    await callback_query.message.answer_photo(
        photo=IMAGES["results"],
        caption="Результаты и отзывы моих учеников.",
        reply_markup=results_menu_markup()
    )

# Обработчик кнопки "ОБРАТНАЯ СВЯЗЬ"
@dp.callback_query(F.data == "feedback")
async def feedback_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["feedback"], caption="Чтобы задать дополнительные вопросы и узнать подробнее о практиках напишите мне @dariakobrina."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "ТАРИФ И ОПЛАТА" для групповых практик
@dp.callback_query(F.data == "tariff_group")
async def tariff_group_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["tariff"], caption="Приобретите нужную подписку по актуальной стоимости:\n\nПОДПИСКА 1 МЕСЯЦ - 2.450 ₽.\nПОДПИСКА 3 МЕСЯЦА - 6.835 ₽.\nПОДПИСКА 6 МЕСЯЦЕВ 12.495 ₽.\n\n💳 Вы можете оплатить подписку любой картой РФ банка или иностранного банка.\n\n💱Также доступна оплата криптовалютой (USDT). Условия оплаты криптой смотрите далее в разделе «ОПЛАТИТЬ КРИПТОЙ»."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ОПЛАТА", callback_data="payment_group")],
            [InlineKeyboardButton(text="НАЗАД", callback_data="group_practice")],
            [InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "ОПЛАТИТЬ" для групповых практик
@dp.callback_query(F.data == "payment_group")
async def payment_group_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["tariff"], caption="Выберите нужную подписку"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ПОДПИСКА 1 МЕСЯЦ", url="https://payform.ru/qs5XszQ/")],
            [InlineKeyboardButton(text="ПОДПИСКА 3 МЕСЯЦА", url="https://payform.ru/795VRyo/")],
            [InlineKeyboardButton(text="ПОДПИСКА 6 МЕСЯЦЕВ", url="https://payform.ru/9q5VRzJ/")],
            [InlineKeyboardButton(text="ОПЛАТИТЬ КРИПТОЙ", callback_data="payment_crypto")],
            [InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "ОПЛАТИТЬ КРИПТОЙ" для групповых практик
@dp.callback_query(F.data == "payment_crypto")
async def payment_crypto_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["tariff"], caption="Стоимость в USDT:\n\nПОДПИСКА 1 МЕСЯЦ - 24$\nПОДПИСКА 3 МЕСЯЦА - 68$\nПОДПИСКА 6 МЕСЯЦЕВ - 124$\n\nСеть - TRC 20\nTMrL9Yk1Mse7yLAbKdqeTC8DztwRhr9Ptk\n\nБудьте внимательны при копировании адреса кошелька. Перед совершением оплаты убедитесь в корректности адреса.\n\nПосле совершения оплаты сделайте скрин-шот успешной операции и нажмите на кнопку ниже и отправьте скрин-шот успешной операции."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ОПЛАТИЛ(А) - ОТПРАВИТЬ СКРИН", url="https://t.me/dariakobrina")],
            [InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "ТАРИФ И ОПЛАТА" для индивидуальных практик
@dp.callback_query(F.data == "tariff_individual")
async def tariff_individual_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["tariff"], caption="💲Актуальная стоимость:\n\nОдно занятие - 3.000₽.\nАбонемент на месяц (8 практик) - 24.000 ₽.\n\n💱Crypto (USDT)\n\nОдно занятие - 30$\nАбонемент на месяц (8 практик) - 240$\n\n💳 Вы можете оплатить подписку любой картой РФ банка.\n\n💱Также доступна оплата криптовалютой (USDT).\n\nЧтобы записаться на индивидуальную практику нажмите кнопку «ЗАПИСАТЬСЯ НА ПРАКТИКУ» и напишите мне."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ЗАПИСАТЬСЯ НА ПРАКТИКУ", url="https://t.me/dariakobrina")],
            [InlineKeyboardButton(text="НАЗАД", callback_data="individual_practice")],
            [InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]
        ])
    )

# Обработчик кнопки "НАЗАД"
@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(callback_query: types.CallbackQuery):
    await callback_query.message.edit_media(
        types.InputMediaPhoto(media=IMAGES["main"], caption="Привет! \n\nМеня зовут Даша, я тренер по йоге с опытом более 4 лет. Если ты устал от болей в спине, стресса на работе или недостатка энергии, ты пришел по адресу!\n\nЯ помогу тебе:\n✨ Избавиться от болей в теле и улучшить осанку\n✨ Оберечь внутренний баланс и спокойствие\n✨ Поднять уровень энергии и снять стресс, даже если у тебя очень плотный график.\n\nВ этом боте ты можешь узнать все о моих занятиях, тарифах и условиях. Готов улучшить свое тело и настроение? Давай начнем прямо сейчас!\n\nВыбери, что тебе интересно и давай сделаем первый шаг к здоровью!"),
        reply_markup=main_menu()
    )

# Обработчик кнопки "ПОДПИСКА 1 МЕСЯЦ"
@dp.callback_query(F.data == "subscription_1_month")
async def subscription_1_month_handler(callback_query: types.CallbackQuery):
    client_id = callback_query.from_user.id
    process_purchase(client_id, 30)  # Указываем количество дней подписки
    await callback_query.message.answer("Спасибо за покупку! Ваша подписка на 1 месяц активирована.")

# Обработчик кнопки "ПОДПИСКА 3 МЕСЯЦА"
@dp.callback_query(F.data == "subscription_3_months")
async def subscription_3_months_handler(callback_query: types.CallbackQuery):
    client_id = callback_query.from_user.id
    process_purchase(client_id, 90)  # Указываем количество дней подписки
    await callback_query.message.answer("Спасибо за покупку! Ваша подписка на 3 месяца активирована.")

# Обработчик кнопки "ПОДПИСКА 6 МЕСЯЦЕВ"
@dp.callback_query(F.data == "subscription_6_months")
async def subscription_6_months_handler(callback_query: types.CallbackQuery):
    client_id = callback_query.from_user.id
    process_purchase(client_id, 180)  # Указываем количество дней подписки
    await callback_query.message.answer("Спасибо за покупку! Ваша подписка на 6 месяцев активирована.")

# Секретный ключ Prodamus
PRODAMUS_SECRET_KEY = "37bc20c9d78758f336c5777b955ece74733e7fc31d42132c965d92f7f78c6f51"

# Функция для проверки подлинности уведомления от Prodamus
def verify_prodamus_signature(data, signature):
    expected_signature = hmac.new(PRODAMUS_SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

# Функция для обработки уведомлений от Prodamus
async def handle_prodamus_webhook(request):
    data = await request.text()
    signature = request.headers.get('X-Signature')

    if not verify_prodamus_signature(data, signature):
        return web.Response(status=403)

    payload = json.loads(data)
    user_id = payload['user_id']
    subscription_duration = payload['subscription_duration']

    process_purchase(user_id, subscription_duration)
    await send_subscription_message(user_id, subscription_duration)

    return web.Response(status=200)

# Функция для отправки сообщения о подписке
async def send_subscription_message(user_id, subscription_duration):
    if subscription_duration == 30:
        message = "Спасибо за покупку! Ваша подписка на 1 месяц активирована."
    elif subscription_duration == 90:
        message = "Спасибо за покупку! Ваша подписка на 3 месяца активирована."
    elif subscription_duration == 180:
        message = "Спасибо за покупку! Ваша подписка на 6 месяцев активирована."
    else:
        message = "Спасибо за покупку! Ваша подписка активирована."

    await bot.send_message(chat_id=user_id, text=message)

# Главная функция запуска бота
async def main():
    dp.startup.register(lambda: print("Бот запущен"))
    dp.message.register(send_welcome)
    dp.callback_query.register(group_practice_menu, F.data == "group_practice")
    dp.callback_query.register(individual_practice_menu, F.data == "individual_practice")
    dp.callback_query.register(trial_practice_menu, F.data == "trial_practice")
    dp.callback_query.register(results_menu, F.data == "results")
    dp.callback_query.register(feedback_menu, F.data == "feedback")
    dp.callback_query.register(tariff_group_menu, F.data == "tariff_group")
    dp.callback_query.register(payment_group_menu, F.data == "payment_group")
    dp.callback_query.register(tariff_individual_menu, F.data == "tariff_individual")
    dp.callback_query.register(main_menu_handler, F.data == "main_menu")
    dp.callback_query.register(subscription_1_month_handler, F.data == "subscription_1_month")
    dp.callback_query.register(subscription_3_months_handler, F.data == "subscription_3_months")
    dp.callback_query.register(subscription_6_months_handler, F.data == "subscription_6_months")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Основной цикл проверки подписок и отправки напоминаний
async def check_subscriptions_and_send_reminders():
    while True:
        # Проверка подписок каждые 24 часа
        check_subscriptions()

        # Отправка напоминаний клиентам, которые запустили бота, но не сделали покупку
        for client in clients_collection.find({'subscription_status': 'no_subscription'}):
            # Проверка наличия поля 'user_id'
            if 'user_id' in client:
                # Условие для отправки напоминания только один раз через 5 минут
                if not client.get('reminder_sent', False):  # Напоминание еще не отправлено
                    if client['last_reminder'] is None or client['last_reminder'] <= time.time() - 2 * 60:
                        await send_reminder(client['user_id'])

                        # Обновление времени последнего напоминания и состояния
                        clients_collection.update_one(
                            {'user_id': client['user_id']},
                            {
                                '$set': {
                                    'last_reminder': time.time(),
                                    'reminder_sent': True  # Отмечаем, что напоминание отправлено
                                }
                            }
                        )
            else:
                print(f"Ошибка: отсутствует поле 'user_id' в документе: {client}")

        # Ожидание 5 минут перед следующей проверкой
        await asyncio.sleep(2 * 60)

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post('/prodamus_webhook', handle_prodamus_webhook)

    web.run_app(app, port=8080)
    asyncio.run(main())
    asyncio.run(check_subscriptions_and_send_reminders())
