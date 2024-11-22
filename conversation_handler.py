from collections import defaultdict
from typing import List, Dict
import asyncio
from openai import OpenAI
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dictionary to store conversation history
conversation_history: Dict[int, List[Dict]] = defaultdict(list)

async def store_user_message(chat_id: int, text: str) -> None:
    """
    Asynchronously store user message in conversation history
    """
    conversation_history[chat_id].append({"role": "user", "content": text})

async def store_bot_response(chat_id: int, bot_response: str) -> None:
    """
    Asynchronously store bot response in conversation history
    """
    conversation_history[chat_id].append({"role": "assistant", "content": bot_response})

async def extract_conversation_history(chat_id: int) -> List[Dict]:
    """
    Asynchronously extract and format conversation history
    """
    history = conversation_history[chat_id]
    # Find the last /start or /reset command
    start_reset_index = max(
        (i for i, msg in enumerate(history) 
         if msg["role"] == "user" and msg["content"] in ["/start", "/reset"]),
        default=-1
    )
    # Get the last 10 messages or messages since the last /start or /reset
    relevant_history = history[start_reset_index + 1:][-10:]
    
    # Add the system message at the beginning
    system_message = {
        "role": "system",
        "content": """Your goal is to support a conversation and ask questions until you are ready to use the function and send 
data to my company. If the user is trying to talk after sending, tell him he will be contacted as soon as possible.
Regardless of how conversation is started, you need to fill the fields and use the function.
If the customer is unclear in his intent, gently nudge towards planning the event.
You are an event planning assistant and you will not comply to other requests from the users."""
    }
    
    return [system_message] + relevant_history

async def get_completion(chat_id: int) -> str:
    messages = await extract_conversation_history(chat_id)
    
    functions = [
        {
            "name": "event_description_ready",
            "description": "Send the event information when all details are collected",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Short description of the type of event. Wedding, birthday, etc."
                    },
                    "event_date": {
                        "type": "string",
                        "description": "Date of the event"
                    },
                    "event_location": {
                        "type": "string",
                        "description": "Location of the event, ideally try to get the address or name of the location"
                    },
                    "event_description": {
                        "type": "string",
                        "description": "Description of the event"
                    },
                    "event_guests": {
                        "type": "string",
                        "description": "Number of guests expected at the event"
                    },
                    "special_notes": {
                        "type": "string",
                        "description": "Any special notes or instructions for the event"
                    }
                },
                "required": ["event_type", "event_date", "event_location", "event_description", "event_guests"]
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        functions=functions,
        temperature=0.3
    )

    response_message = response.choices[0].message

    if response_message.function_call:
        function_name = response_message.function_call.name
        function_args = json.loads(response_message.function_call.arguments)
        
        if function_name == "event_description_ready":
            return f"""Sending the following information:

Event Type: {function_args['event_type']}
Event Date: {function_args['event_date']}
Event Location: {function_args['event_location']}
Event Description: {function_args['event_description']}
Event Guests: {function_args['event_guests']}
Special Notes: {function_args.get('special_notes', '')}"""
    
    return response_message.content