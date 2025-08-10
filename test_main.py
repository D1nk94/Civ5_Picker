
import pytest
from types import SimpleNamespace
from telegram import InlineKeyboardButton

from main import setup_callback

class FakeMessage:
    def __init__(self):
        self.texts = []

    async def edit_text(self, text, reply_markup=None):
        self.texts.append(text)
        self.reply_markup = reply_markup

class FakeCallbackQuery:
    def __init__(self, data):
        self.data = data
        self.message = FakeMessage()

    async def answer(self):
        pass

@pytest.mark.asyncio
async def test_ab1_question():
    query = FakeCallbackQuery(data="picks|3")
    context = SimpleNamespace()
    await setup_callback(SimpleNamespace(callback_query=query), context)
    found = any("Испанию" in text or "Венецию" in text for text in query.message.texts)
    assert found, "Не задан вопрос об Испании и Венеции"

@pytest.mark.asyncio
async def test_ab2_question():
    query = FakeCallbackQuery(data="ab1|yes")
    context = SimpleNamespace()
    await setup_callback(SimpleNamespace(callback_query=query), context)
    found = any("Данию" in text or "Корею" in text for text in query.message.texts)
    assert found, "Не задан вопрос о Дании, Вавилоне, Корее и Полинезии"

@pytest.mark.asyncio
async def test_final_message():
    query = FakeCallbackQuery(data="ab2|yes")
    context = SimpleNamespace()
    await setup_callback(SimpleNamespace(callback_query=query), context)
    found = any("Автобан" in text for text in query.message.texts)
    assert found, "Финальное сообщение не содержит список автобанов"
