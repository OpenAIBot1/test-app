from fastapi import FastAPI
import httpx
import asyncio
import logging
from typing import Optional
from pydantic import BaseModel
from conversation_handler import store_user_message, store_bot_response, extract_conversation_history, get_completion
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

class TelegramMessage(BaseModel):
    chat: dict
    text: Optional[str] = None

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

# Global variable to store the polling task
polling_task = None

async def poll_telegram():
    """Poll Telegram for updates using proper async patterns"""
    offset = 0
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{TELEGRAM_API_URL}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=35.0
                )
                
                if response.status_code == 409:
                    logger.warning("Conflict: Another instance is running. Shutting down this polling instance.")
                    return
                
                if response.status_code != 200:
                    logger.error(f"Failed to get updates: {response.text}")
                    await asyncio.sleep(5)
                    continue

                updates = response.json().get("result", [])
                
                for update in updates:
                    try:
                        update_obj = TelegramUpdate(**update)
                        offset = update_obj.update_id + 1

                        if update_obj.message and update_obj.message.text:
                            chat_id = update_obj.message.chat.get("id")
                            text = update_obj.message.text

                            logger.info(f"Received message from chat_id {chat_id}: {text}")

                            # Process message and get response
                            bot_response = await process_message(text, chat_id)

                            # Send response
                            await send_message(chat_id, bot_response)

                    except Exception as e:
                        logger.error(f"Error processing update: {str(e)}")
                        continue

        except httpx.TimeoutException:
            continue
        except asyncio.CancelledError:
            logger.info("Polling task was cancelled")
            return
        except Exception as e:
            logger.error(f"Polling error: {str(e)}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Start the polling task"""
    global polling_task
    polling_task = asyncio.create_task(poll_telegram())
    logger.info("Started Telegram polling task")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup polling task"""
    global polling_task
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped Telegram polling task")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "mode": "polling"}

@app.get("/status")
async def status():
    """Check if polling is active"""
    is_polling = polling_task and not polling_task.done()
    return {
        "polling_active": is_polling,
        "bot_token_configured": bool(TELEGRAM_BOT_TOKEN)
    }
