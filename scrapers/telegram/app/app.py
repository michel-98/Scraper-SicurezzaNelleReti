import asyncio
import os

from telethon.errors import ChatAdminRequiredError
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, ChatForbidden
import json
from flask_restful import Api, request
from flask import Flask

app = Flask(__name__)
api = Api(app)

@app.get('/telegram_messages')
def telegram_messages():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    args = request.args
    print(args)
    api_id = args.get("api_id", type=int)
    api_hash = args.get("api_hash")
    phone = "+39" + args.get("phone")
    code_from_app = args.get("session_code")
    client = TelegramClient(phone, api_id, api_hash)

    client.connect()
    if not client.is_user_authorized():
        try:
            client.sign_in(phone, code_from_app, phone_code_hash=os.getenv('PHONE_CODE_HASH'))
        except Exception as e:
            print(str(e))
            os.environ['PHONE_CODE_HASH'] = client.send_code_request(phone).phone_code_hash
            return "Client unauthorized: invalid auth code. Check your phone to see if the code is correct."

    chats = []
    last_date = None
    chunk_size = 200
    groups = []

    result = client(GetDialogsRequest(
        offset_date=last_date,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=chunk_size,
        hash=0
    ))
    chats.extend(result.chats)
    for chat in chats:
        try:
            if (not isinstance(chat, ChatForbidden)) and (chat.participants_count != 0):
                groups.append(chat)
        except Exception as e:
            print(e)
            continue

    print('Fetching Messages...')
    messages_JSONS = []
    message_data = {}

    for i in range(len(groups)):
        try:
            print(str(i) + '- ' + groups[i].title)
            all_messages = client.get_messages(groups[i], limit=200)
            for message in all_messages:
                message_data["id"] = message.id
                message_data["date"] = message.date.strftime("%m/%d/%Y, %H:%M:%S")
                message_data["text"] = message.text if message.text is not None else ""
                message_data["sender"] = {
                    "type": message.sender.__class__.__name__,
                    "username": message.sender.username,
                    "id": message.sender.id,
                    "verified": message.sender.verified
                } if message.sender is not None else None
                message_data["type"] = message.id
                message_data["chat"] = {
                    "title": message.chat.title if message.chat.title is not None else "",
                    "participants_count": message.chat.participants_count,
                    "id": message.chat.id
                } if message.chat is not None else None
                message_data["is_reply"] = message.is_reply
                message_data["pinned"] = message.pinned
                messages_JSONS.append(json.dumps(message_data, sort_keys=True))
            print('Scraped')
        except ChatAdminRequiredError:
            continue
    client.disconnect()
    return messages_JSONS


if __name__ == "__main__":
    app.run(port=5001)
