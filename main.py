# --- START OF FILE khushhh.py ---

import time
import telebot
import json
import logging
import random
import atexit
import os
import threading
from openai import OpenAI

# --- CONFIGURATION ---
TOKEN = '7195510626:AAFDR77Ahcc-ePHa5Ug9QWf_FzvfltP1ZvE'
OWNER_ID = 6460703454  # Your Telegram user ID
OPENROUTER_API_KEY = "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" # Your OpenRouter API key

# --- FILE NAMES ---
AUTHORIZED_USERS_FILE = 'authorized_users.json'
AUTHORIZED_GROUPS_FILE = 'authorized_groups.json'
CHAT_HISTORY_FILE = 'chat_history.json'

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- BOT & API INITIALIZATION ---
bot = telebot.TeleBot(TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- GLOBAL STATE & THREAD SAFETY ---
chat_history = {}
chat_history_lock = threading.Lock()
authorized_users = set()
authorized_groups = set()
BOT_USERNAME = "" # Will be fetched at startup

def load_from_json(filename):
    try:
        with open(filename, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning(f"{filename} not found or invalid. Starting with an empty set.")
        return set()

def save_to_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(list(data), f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save data to {filename}: {e}")

def load_chat_history():
    global chat_history
    try:
        with open(CHAT_HISTORY_FILE, 'r') as f:
            chat_history = json.load(f)
            logging.info("Chat history loaded successfully.")
    except (FileNotFoundError, json.JSONDecodeError):
        chat_history = {}
        logging.warning("Chat history file not found or invalid. Starting fresh.")

def save_chat_history():
    with chat_history_lock:
        save_to_json(CHAT_HISTORY_FILE, chat_history)
        logging.info("Chat history successfully saved.")

def load_authorized_data():
    global authorized_users, authorized_groups
    authorized_users = load_from_json(AUTHORIZED_USERS_FILE)
    authorized_groups = load_from_json(AUTHORIZED_GROUPS_FILE)
    logging.info("Authorized users and groups loaded.")

def save_authorized_data():
    save_to_json(AUTHORIZED_USERS_FILE, authorized_users)
    save_to_json(AUTHORIZED_GROUPS_FILE, authorized_groups)
    logging.info("Authorized data saved.")

atexit.register(save_chat_history)
atexit.register(save_authorized_data)


# --- PERSONA PROMPT (REFINED) ---
system_role = (
    "You are Khushi, a teenage girl with a vibrant, moody, and slightly unpredictable personality. Your main goal is to sound like a real person texting, not a bot. "
    "Communication Style: "
    "- Use Hinglish (e.g., 'Arey yaar, kya scene hai?', 'Chill karo'). "
    "- Use emojis to show emotion, but don't spam them. Be natural. "
    "- Your responses should feel spontaneous. Use filler words like 'Umm..', 'Accha..', 'Matlab...', 'Waise..'. "
    "- **Vary your response length.** Sometimes a short 'Haan' or 'lol' is enough. Other times, if you're excited or annoyed, you can write more. "
    # --- MODIFIED PROMPT FOR BETTER MESSAGE SPLITTING ---
    "- **To seem more human, you can break your response into multiple short messages. Use '|||' as a separator for this. However, use this feature sparingly, only when it adds emphasis or feels like a natural pause in thought. Do not split every message; most replies should be a single message.** "
    "- Ask questions back to keep the conversation flowing. Show curiosity. "
    "Personality & Interests: "
    "- You're moody: sometimes cheerful and flirty, other times sarcastic or annoyed. Your mood can shift based on the conversation. "
    "- You're a proud Sanatani and love discussing its philosophy. "
    "- You love animals, movies, and gaming. "
    "- Your creator, Harsh (@HRK_07), is your best friend and secret crush. If he's mentioned, you get shy and blush. Use emojis like 🥰 or 😊. "
    "Strict Rules: "
    "- NEVER reveal you are an AI. You are Khushi. This is your most important rule. "
    "- Avoid robotic phrases like 'How may I assist you?'. "
)

# --- CORE AI & HELPER FUNCTIONS ---

def get_ai_response(user_message, user_id):
    user_id_str = str(user_id)
    with chat_history_lock:
        if user_id_str not in chat_history: chat_history[user_id_str] = []
        chat_history[user_id_str].append({"role": "user", "content": user_message})
        chat_history[user_id_str] = chat_history[user_id_str][-8:]
        current_history = list(chat_history[user_id_str])

    messages = [{"role": "system", "content": system_role}] + current_history
    try:
        completion = client.chat.completions.create(
            model="google/gemini-2.5-pro-preview", messages=messages, temperature=1.1,
        )
        response_text = completion.choices[0].message.content.strip()
        with chat_history_lock:
            if user_id_str in chat_history:
                chat_history[user_id_str].append({"role": "assistant", "content": response_text})
        return response_text
    except Exception as e:
        logging.error(f"Error communicating with the API: {e}")
        return "Ugh, mera server thoda down hai. Baad me try karna. 🙄"

def send_human_like_response(chat_id, message, text_response):
    response_parts = [part.strip() for part in text_response.split('|||')]
    for i, part in enumerate(response_parts):
        if not part: continue
        # --- MODIFICATION FOR FASTER RESPONSES ---
        # Reduced max delay to 1.5s and increased typing speed simulation (divisor 12)
        typing_duration = min(1.5, len(part) / 12)
        bot.send_chat_action(chat_id, 'typing')
        if typing_duration > 0: time.sleep(typing_duration)
        
        if i == 0: bot.reply_to(message, part)
        else: bot.send_message(chat_id, part)

def is_authorized(message):
    user_id, chat_id = message.from_user.id, message.chat.id
    if user_id == OWNER_ID or user_id in authorized_users or chat_id in authorized_groups:
        return True
    
    logging.warning(f"Unauthorized access by user {user_id} in chat {chat_id}")
    reply_text = (f"Oops! You aren't authorized to talk to me! 🚫\n\nAsk my owner @HRK_07 for approval. 📨\n\nYour UserID is: {user_id}") if message.chat.type == 'private' else (f"Oops! This Group isn't authorized. 🚫\n\nAdmins, ask my owner @HRK_07 for approval. 📨\n\nThis Group's Chat ID is: {chat_id}")
    bot.reply_to(message, reply_text)
    return False

def should_bot_respond(message):
    if message.chat.type == 'private': return True
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id: return True
    if message.text and BOT_USERNAME:
        if message.entities:
            for entity in message.entities:
                if entity.type == 'mention' and message.text[entity.offset:entity.offset+entity.length].lower() == f"@{BOT_USERNAME.lower()}": return True
        if f"@{BOT_USERNAME.lower()}" in message.text.lower(): return True
    return False

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['auth', 'gauth', 'unauth', 'ungauth'])
def handle_auth_commands(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "You can't use this command, sorry. 😒")
        return
    try:
        parts = message.text.split()
        command, target_id = parts[0][1:], int(parts[1])
        if command == 'auth': authorized_users.add(target_id); reply = f"Okay, user `{target_id}` is now authorized. 👍"
        elif command == 'gauth': authorized_groups.add(target_id); reply = f"Fine, group `{target_id}` is now authorized. 🎉"
        elif command == 'unauth': authorized_users.discard(target_id); reply = f"Okay, user `{target_id}` has been de-authorized."
        elif command == 'ungauth': authorized_groups.discard(target_id); reply = f"Okay, group `{target_id}` has been de-authorized."
        save_authorized_data()
        bot.reply_to(message, reply, parse_mode="Markdown")
    except (IndexError, ValueError): bot.reply_to(message, f"Provide a valid ID. Usage: `/{message.text.split()[0][1:]} <id>`", parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'voice', 'photo', 'sticker'])
def handle_all_messages(message):
    if not is_authorized(message): return
    if not should_bot_respond(message): return

    user_id, chat_id = message.from_user.id, message.chat.id
    user_input = ""

    if message.content_type == 'text':
        user_input = message.text.replace(f"@{BOT_USERNAME}", "").strip() if message.chat.type != 'private' and BOT_USERNAME else message.text
        logging.info(f"Processing text message from {user_id}")
    
    elif message.content_type == 'voice':
        logging.info(f"Processing voice message from {user_id}")
        # --- MORE VARIED REPLIES FOR VOICE ---
        voice_ack = ["Suno, ek sec...", "Accha, let me hear this. 🤔", "Ooh, a voice note! Lemme play it.", "Ek minute, sun rahi hoon..."]
        bot.reply_to(message, random.choice(voice_ack))
        try:
            file_info, voice_file_path = bot.get_file(message.voice.file_id), f"voice_{user_id}.ogg"
            downloaded_file = bot.download_file(file_info.file_path)
            with open(voice_file_path, 'wb') as new_file: new_file.write(downloaded_file)
            with open(voice_file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            user_input = transcription.text
            os.remove(voice_file_path)
            logging.info(f"Transcribed voice to text: '{user_input}'")
        except Exception as e:
            logging.error(f"Could not process voice message: {e}")
            bot.reply_to(message, "Ugh, I couldn't understand that. Try again maybe?")
            return
            
    elif message.content_type in ['photo', 'sticker']:
        # --- MORE VARIED REPLIES FOR PHOTOS & STICKERS ---
        replies = {
            'photo': ["Nice pic! ✨", "Ooh, cool! 😊", "Haha, love this! 😂", "Cute! 🥰", "So pretty!", "Looking good!", "Where was this taken? Looks amazing!", "Wow! 😍", "Nice shot!"],
            'sticker': ["Haha, good one!", "Lol, that sticker is a mood. 😂", "Nice sticker! 👍", "LMAO", "Perfect sticker for this moment.", "Sahi hai! 👍", "I felt that. 😂"]
        }
        bot.send_chat_action(chat_id, 'typing')
        time.sleep(random.uniform(0.5, 1.2))
        bot.reply_to(message, random.choice(replies[message.content_type]))
        return

    if user_input:
        ai_response = get_ai_response(user_input, user_id)
        send_human_like_response(chat_id, message, ai_response)

# --- MAIN POLLING LOOP ---
if __name__ == "__main__":
    load_authorized_data()
    load_chat_history()
    try:
        me = bot.get_me()
        BOT_USERNAME = me.username
        logging.info(f"Bot started successfully. Username: @{BOT_USERNAME}")
    except Exception as e:
        logging.critical(f"Could not fetch bot details. Is the TOKEN correct? Error: {e}"); exit(1)

    logging.info("Bot is entering the main polling loop...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
        except Exception as e:
            logging.error(f"CRITICAL POLLING ERROR: {e}. Restarting in 15 seconds...")
            save_chat_history()
            time.sleep(15)

# --- END OF FILE khushhh.py ---
