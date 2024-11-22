from fastapi import FastAPI
import httpx
import asyncio
import logging
from typing import Optional
from pydantic import BaseModel
from conversation_handler import store_user_message, store_bot_response, extract_conversation_history, say_hello_to_user, message_history

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = '7516762763:AAHWYgVMX7ZrWkH5HpWvPEAhogdKMdEQAWY'
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
    async with httpx.AsyncClient() as client:
        payload = {"chat_id": chat_id, "text": text}
        try:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage", 
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send message to chat_id {chat_id}: {str(e)}")

async def process_message(text: str, chat_id: int) -> str:
    """Process incoming messages and return appropriate responses"""
    if text == "/start":
        return "Welcome! How can I assist you today?"
    elif text == "/reset":
        return "Resetting your session."
    elif text == "/history":
        return await extract_conversation_history(chat_id)
    else:
        resp = say_hello_to_user(message_history)
        if resp.tool_calls:
            tool_results = resp.call_tools_and_collect_as_message()
            return f"{tool_results.text_only}"
        return f"{resp.text}"

async def poll_telegram():
    """Poll Telegram for updates using proper async patterns"""
    offset = 0
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(
                    f"{TELEGRAM_API_URL}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=35.0
                )
                
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

                            # Store user message
                            await store_user_message(chat_id, text)

                            # Process message and get response
                            bot_response = await process_message(text, chat_id)

                            # Send and store response
                            await send_message(chat_id, bot_response)
                            await store_bot_response(chat_id, bot_response)

                    except Exception as e:
                        logger.error(f"Error processing update: {str(e)}")
                        continue

            except httpx.TimeoutException:
                continue
            except Exception as e:
                logger.error(f"Polling error: {str(e)}")
                await asyncio.sleep(5)

async def startup_event():
    """Start the polling task"""
    app.state.polling_task = asyncio.create_task(poll_telegram())
    logger.info("Started Telegram polling task")

async def shutdown_event():
    """Cleanup polling task"""
    if hasattr(app.state, 'polling_task'):
        app.state.polling_task.cancel()
        try:
            await app.state.polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped Telegram polling task")

# Register startup and shutdown events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "mode": "polling"}

@app.get("/status")
async def status():
    """Check if polling is active"""
    is_polling = hasattr(app.state, 'polling_task') and not app.state.polling_task.done()
    return {
        "polling_active": is_polling,
        "bot_token_configured": bool(TELEGRAM_BOT_TOKEN)
    }
