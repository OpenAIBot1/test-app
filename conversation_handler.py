from collections import defaultdict
import ell
from ell import Message
from typing import List

# Dictionary to store conversation history
conversation_history = defaultdict(list)
message_history = []  # Initialize as an empty list

def store_user_message(chat_id, text):
    conversation_history[chat_id].append(f"User: {text}")
    message_history.append(ell.user(text))

def store_bot_response(chat_id, bot_response):
    conversation_history[chat_id].append(f"Bot: {bot_response}")
    message_history.append(ell.assistant(bot_response))

def extract_conversation_history(chat_id):
    history = conversation_history[chat_id]
    # Find the last /start or /reset command
    start_reset_index = max(
        (i for i, msg in enumerate(history) if "User: /start" in msg or "User: /reset" in msg),
        default=-1
    )
    # Get the last 10 messages or messages since the last /start or /reset
    relevant_history = history[start_reset_index + 1:]
    return "\n".join(relevant_history[-10:])

# @ell.simple()
# def say_hello_to_user
