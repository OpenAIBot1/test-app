from fastapi import FastAPI
import httpx
import asyncio
import logging
import sys
from typing import Optional
from pydantic import BaseModel
from conversation_handler import store_user_message, store_bot_response, extract_conversation_history, get_completion
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(stream=sys.stdout)
    ]
)

# Redirect warnings and below to stdout
logging.getLogger().handlers[0].setStream(sys.stdout)

# Create a separate handler for errors to stderr
error_handler = logging.StreamHandler(stream=sys.stderr)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))
logging.getLogger().addHandler(error_handler)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
WEBHOOK_URL = "https://web-production-1d22.up.railway.app"  # Your Railway app URL

class TelegramMessage(BaseModel):
    message_id: int
    chat: dict
    text: Optional[str] = None
    date: int

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None

app = FastAPI()

async def send_message(chat_id: int, text: str):
    """Asynchronously send message to Telegram"""
    logger.info(f"Sending message to chat_id {chat_id}")
    async with httpx.AsyncClient() as client:
        payload = {"chat_id": chat_id, "text": text}
        try:
            logger.debug(f"Making Telegram API request to /sendMessage for chat_id {chat_id}")
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage", 
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Successfully sent message to chat_id {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send message to chat_id {chat_id}: {str(e)}", exc_info=True)

async def process_message(text: str, chat_id: int) -> str:
    """Process incoming messages and return appropriate responses"""
    logger.info(f"Processing message from chat_id {chat_id}: {text[:50]}...")
    
    # Store user message first
    await store_user_message(chat_id, text)
    
    if text == "/start":
        response = "Welcome! How can I assist you today?"
        logger.info(f"Sending welcome message to chat_id {chat_id}")
    elif text == "/reset":
        response = "Resetting your session."
        logger.info(f"Resetting session for chat_id {chat_id}")
    elif text == "/history":
        logger.info(f"Retrieving history for chat_id {chat_id}")
        history = await extract_conversation_history(chat_id)
        response = "\n".join([msg["content"] for msg in history])
    else:
        response = await get_completion(chat_id)
    
    # Store bot response
    await store_bot_response(chat_id, response)
    return response

@app.post("/webhook")
async def webhook(update: TelegramUpdate):
    logger.info(f"Received webhook update: {update}")
    if update.message and update.message.text:
        chat_id = update.message.chat["id"]
        logger.info(f"Processing message: {update.message.text} from chat_id: {chat_id}")
        response = await process_message(update.message.text, chat_id)
        logger.info(f"Sending response: {response}")
        await send_message(chat_id, response)
    else:
        logger.warning(f"Received update without message or text: {update}")
    return {"ok": True}

@app.on_event("startup")
async def setup_webhook():
    async with httpx.AsyncClient() as client:
        webhook_info_url = f"{TELEGRAM_API_URL}/getWebhookInfo"
        webhook_info = await client.get(webhook_info_url)
        
        if webhook_info.json()["result"]["url"] != f"{WEBHOOK_URL}/webhook":
            # Delete any existing webhook
            await client.get(f"{TELEGRAM_API_URL}/deleteWebhook")
            
            # Set the webhook
            webhook_url = f"{TELEGRAM_API_URL}/setWebhook"
            params = {
                "url": f"{WEBHOOK_URL}/webhook",
                "allowed_updates": ["message"]
            }
            response = await client.post(webhook_url, params=params)
            if response.status_code == 200:
                logger.info("Webhook set successfully")
            else:
                logger.error(f"Failed to set webhook: {response.text}")

@app.on_event("shutdown")
async def remove_webhook():
    async with httpx.AsyncClient() as client:
        # Delete the webhook when shutting down
        await client.get(f"{TELEGRAM_API_URL}/deleteWebhook")
        logger.info("Webhook removed")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "mode": "webhook"}

@app.get("/status")
async def status():
    """Check if webhook is active"""
    return {
        "webhook_active": True,
        "bot_token_configured": bool(TELEGRAM_BOT_TOKEN)
    }
