from collections import defaultdict
from typing import List, Dict
import asyncio
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    logger.info(f"Storing user message for chat_id {chat_id}: {text[:50]}...")
    conversation_history[chat_id].append({"role": "user", "content": text})

async def store_bot_response(chat_id: int, bot_response: str) -> None:
    """
    Asynchronously store bot response in conversation history
    """
    logger.info(f"Storing bot response for chat_id {chat_id}: {bot_response[:50]}...")
    conversation_history[chat_id].append({"role": "assistant", "content": bot_response})

async def extract_conversation_history(chat_id: int) -> List[Dict]:
    """
    Asynchronously extract and format conversation history
    """
    logger.info(f"Extracting conversation history for chat_id {chat_id}")
    history = conversation_history[chat_id]
    # Find the last /start or /reset command
    start_reset_index = max(
        (i for i, msg in enumerate(history) 
         if msg["role"] == "user" and msg["content"] in ["/start", "/reset"]),
        default=-1
    )
    relevant_history = history[start_reset_index + 1:][-10:]
    logger.debug(f"Retrieved {len(relevant_history)} relevant messages for chat_id {chat_id}")
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
    logger.info(f"Getting completion for chat_id {chat_id}")
    messages = await extract_conversation_history(chat_id)
    logger.debug(f"Prepared {len(messages)} messages for OpenAI API")
    
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

    try:
        logger.info(f"Making OpenAI API call for chat_id {chat_id}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions,
            temperature=0.3
        )
        logger.info(f"Received OpenAI API response for chat_id {chat_id}")
        logger.debug(f"OpenAI response tokens: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")

        response_message = response.choices[0].message

        if response_message.function_call:
            logger.info(f"Function call detected: {response_message.function_call.name}")
            function_name = response_message.function_call.name
            function_args = json.loads(response_message.function_call.arguments)
            logger.debug(f"Function arguments: {function_args}")
            
            if function_name == "event_description_ready":
                result = f"""Sending the following information:

Event Type: {function_args['event_type']}
Event Date: {function_args['event_date']}
Event Location: {function_args['event_location']}
Event Description: {function_args['event_description']}
Event Guests: {function_args['event_guests']}
Special Notes: {function_args.get('special_notes', '')}"""
                logger.info(f"Prepared event description response for chat_id {chat_id}")
                return result
        
        logger.info(f"Returning standard message response for chat_id {chat_id}")
        return response_message.content
    except Exception as e:
        logger.error(f"Error in get_completion for chat_id {chat_id}: {str(e)}", exc_info=True)
        raise