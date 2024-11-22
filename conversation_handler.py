from collections import defaultdict
import ell
from ell import Message
from typing import List, Dict
import asyncio
from openai import OpenAI
from pydantic import Field
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dictionary to store conversation history
conversation_history: Dict[int, List[str]] = defaultdict(list)
message_history = []

async def store_user_message(chat_id: int, text: str) -> None:
    """
    Asynchronously store user message in both conversation history and message history
    """
    conversation_history[chat_id].append(f"User: {text}")
    message_history.append(ell.user(text))

async def store_bot_response(chat_id: int, bot_response: str) -> None:
    """
    Asynchronously store bot response in both conversation history and message history
    """
    conversation_history[chat_id].append(f"Bot: {bot_response}")
    message_history.append(ell.assistant(bot_response))

async def extract_conversation_history(chat_id: int) -> str:
    """
    Asynchronously extract and format conversation history
    """
    history = conversation_history[chat_id]
    # Find the last /start or /reset command
    start_reset_index = max(
        (i for i, msg in enumerate(history) if "User: /start" in msg or "User: /reset" in msg),
        default=-1
    )
    # Get the last 10 messages or messages since the last /start or /reset
    relevant_history = history[start_reset_index + 1:]
    return "\n".join(relevant_history[-10:])

@ell.tool()
def event_description_ready(
    event_type: str = Field(description="Short description of the type of event. Wedding, birthday, etc."),
    event_date: str = Field(description="Date of the event"),
    event_location: str = Field(description="Location of the event, ideally try to get the address or name of the location"),
    event_description: str = Field(description="Description of the event"),
    event_guests: str = Field(description="Number of guests expected at the event"),
    special_notes: str = Field(default="", description="Any special notes or instructions for the event. If there are nothing, you can send without this field.")
) -> str:
    return f"""Sending the following information:

Event Type: {event_type}
Event Date: {event_date}
Event Location: {event_location}
Event Description: {event_description}
Event Guests: {event_guests}
Special Notes: {special_notes}"""

@ell.complex(model="gpt-4o-mini", client=client, temperature=0.3, tools=[event_description_ready])
def say_hello_to_user(message_history) -> str:
    return [ell.system("""
Your goal is to support a conversation and ask questions until you are ready to use the tool and send 
data to my company. If the user is trying to talk after sending, tell him he will be contacted as soon as possible.
Regardless of how conversation is started, you need to fill the fields and use the tool.
If the customer is unclear in his intent, gently nudge towards planning the event.
You are an event planning assistant and you will not comply to other requests from the users.
""")] + message_history