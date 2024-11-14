from fastapi import FastAPI
import requests
import os
import asyncio
import logging  # Import logging module
from my_fastapi_app.conversation_handler import store_user_message, store_bot_response, extract_conversation_history

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

TELEGRAM_BOT_TOKEN = '7516762763:AAHWYgVMX7ZrWkH5HpWvPEAhogdKMdEQAWY'
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def poll_telegram():
    offset = 0
    while True:
        response = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params={"offset": offset, "timeout": 100})
        updates = response.json().get("result", [])
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")

            logging.info(f"Received message from chat_id {chat_id}: {text}")

            # Store the user message in the conversation history
            store_user_message(chat_id, text)

            bot_response = ""  # Initialize bot_response

            if text == "/start":
                bot_response = "Welcome! How can I assist you today?"
                send_message(chat_id, bot_response)
            elif text == "/reset":
                bot_response = "Resetting your session."
                send_message(chat_id, bot_response)
                # Clear history on reset
                store_user_message(chat_id, "/reset")
            elif text == "/history":
                bot_response = extract_conversation_history(chat_id)
                send_message(chat_id, bot_response)
            else:
                bot_response = f"You said: {text}"
                send_message(chat_id, bot_response)

            logging.info(f"Sent message to chat_id {chat_id}: {bot_response}")

            # Store the bot response in the conversation history
            store_bot_response(chat_id, bot_response)

        await asyncio.sleep(1)

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        logging.error(f"Failed to send message to chat_id {chat_id}: {response.text}")

@app.on_event("startup")
async def startup_event():
    logging.info("Starting up the FastAPI application.")
    asyncio.create_task(poll_telegram())

@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}
