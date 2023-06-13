import asyncio
import aiogram
import os

from geopy.geocoders import Nominatim

import untitled6
import huff2
import model_prediction

bot = aiogram.Bot('5498974651:AAFxiesEsLcRnrd1RzJEPRqi2gEAc91zlAA')
dp = aiogram.Dispatcher(bot)
geolocator = Nominatim(user_agent="myGeocoder")

keyboard = aiogram.types.ReplyKeyboardMarkup()
keyboard.row('/start', 'Топ-5 мест для магазина', 'Проходимость по адресу', '/quit', '/help')  # Добавлено /help

flag_top = False
flag_pass = False


@dp.message_handler(commands=['start'])
async def welcome(message: aiogram.types.Message):
    await message.answer('Доброго времени суток! Чем я могу помочь?', reply_markup=keyboard)


@dp.message_handler(commands=['quit'])
async def quit(message: aiogram.types.Message):
    await message.answer('Работа бота завершена.')


@dp.message_handler(commands=['help'])
async def help_command(message: aiogram.types.Message):
    response = "Это бот, который может помочь вам с различными задачами. Вот доступные команды:\n"
    response += "/start - Запустить бота\n"
    response += "/help - Показать это сообщение справки\n"
    response += "/command - Выполнить определенную задачу\n"
    await message.answer(response)

async def process_single_shop(i, address_info, chat_id):
    address, lat, lon = address_info
    try:
        if lat is not None and lon is not None:
            await bot.send_message(chat_id, f"Магазин {i}:")
            shop_map = await asyncio.to_thread(huff2.show_nearest_interest_points, lat, lon)
            map_file = f"map{i}.html"
            shop_map.save(map_file)
            with open(map_file, "rb") as file:
                await bot.send_document(chat_id, file)
            os.remove(map_file)
        else:
            await bot.send_message(chat_id, "Не удалось получить координаты для отображения карты.")
    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка при обработке магазина {i}: {str(e)}")
    await asyncio.sleep(1)


async def process_request1(chat_id, name):
    try:
        results = await asyncio.to_thread(untitled6.top5, name)
        if results:
            response = f"Топ 5 магазинов для розничной сети '{name}':\n"
            addresses = []
            for i, elem in enumerate(results, start=1):
                response += f"Магазин {i}:\n"
                response += f"Адрес: {elem['Адрес']}\n"
                response += f"Предполагаемая посещаемость: {round(elem['Предполагаемая посещаемость'])} человек/день\n"
                response += f"Стоимость одного посетителя: {round(elem['Стоимость одного посетителя'])} рублей\n"
                response += f"Стоимость аренды: {round(elem['Стоимость аренды'])} рублей/месяц\n"
                response += f"Площадь: {elem['Площадь']} кв.м.\n"
                response += f"Ссылка на объявление: {elem['Ссылка на объявление']}\n\n"
                lat = elem['Широта']
                lon = elem['Долгота']
                addresses.append((elem['Адрес'], lat, lon))
            await bot.send_message(chat_id, response)
            for i, address_info in enumerate(addresses[:5], start=1):
                try:
                    await process_single_shop(i, address_info, chat_id)
                except Exception as e:
                    await bot.send_message(chat_id, f"Произошла ошибка при обработке магазина {i}: {str(e)}")
        else:
            await bot.send_message(chat_id,
                                   f"Нет данных о магазинах для розничной сети '{name}'. Попробуйте другое название.")
    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка при обработке запроса: {str(e)}")


async def process_request2(chat_id, address, square):
    try:
        location = await asyncio.to_thread(geolocator.geocode, address)
        if location:
            lat = location.latitude
            lon = location.longitude
            if not square.isnumeric():
                await bot.send_message(chat_id, "Некорректное значение площади. Пожалуйста, введите число.")
                return
            square = float(square)
            passability = await asyncio.to_thread(model_prediction.prediction, lat, lon, square)
            await bot.send_message(chat_id, f"Предполагаемая посещаемость: {passability} человек в день")
            shop_map = await asyncio.to_thread(huff2.show_nearest_interest_points, lat, lon)
            map_file = f"map_place.html"
            shop_map.save(map_file)
            with open(map_file, "rb") as file:
                await bot.send_document(chat_id, file)
            os.remove(map_file)
        else:
            await bot.send_message(chat_id, "Не удалось получить координаты для указанного адреса.")
    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка при обработке запроса: {str(e)}")


@dp.message_handler()
async def handle_text(message: aiogram.types.Message):
    global flag_top, flag_pass
    text = message.text.lower()
    chat_id = message.chat.id
    if text == 'топ-5 мест для магазина':
        flag_top = True
        await bot.send_message(chat_id, 'Введите название розничной сети:')
    elif text == 'проходимость по адресу':
        flag_pass = True
        await bot.send_message(chat_id, 'Введите адрес и площадь(через пробел):')
    elif flag_top:
        chat_id = message.chat.id
        name = message.text.lower()
        await bot.send_message(chat_id, 'Анализируем...')
        await process_request1(chat_id, name)
        flag_top = False
    elif flag_pass:
        chat_id = message.chat.id
        text = message.text.lower()
        last_space_index = text.rindex(' ')
        address = text[:last_space_index]
        square = text[last_space_index + 1:]
        await bot.send_message(chat_id, 'Анализируем...')
        await process_request2(chat_id, address, square)
        flag_pass = False
    else:
        await bot.send_message(chat_id, 'Некорректный выбор.')


async def polling():
    await dp.start_polling()


asyncio.run(polling())