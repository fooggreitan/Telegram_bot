from io import BytesIO 
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import telegram
from dotenv import load_dotenv
import os
import openai
from moviepy.editor import AudioFileClip
import time
from gtts import gTTS

def TTV(text: str) -> BytesIO:
    bytsFile = BytesIO()
    try:
        audio = gTTS(text=text, lang="ru")
        audio.write_to_fp(bytsFile)
        bytsFile.seek(0)
    except Exception as e: print(f"Error in TTV: {e}")
    return bytsFile

def simulate_typing_animation(chat_id, context):
    try:
        msg = context.bot.send_message(chat_id=chat_id, text="Бот печатает сообщение...", parse_mode=telegram.ParseMode.MARKDOWN)
        time.sleep(3)
        context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        time.sleep(2)
    except Exception as e:
        print(f"Error in simulate_typing_animation: {e}")

def generate_chatgpt_response(update, context):
    try:
        chat_id = update.effective_chat.id
        message_log[chat_id] = {"role": "user", "content": update.message.text}
        simulate_typing_animation(chat_id, context)
        context.bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
        response = openai.ChatCompletion.create(
            model=modeL,
            messages=[message_log[chat_id]],
            max_tokens=256,
            temperature=0.2,
            top_p=1,
            frequency_penalty=0.5,
            presence_penalty=0.5
        )
        assistant_response = response['choices'][0]['message']['content']
        message_log[chat_id]["assistant_response"] = assistant_response

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Получить голосовое сообщение", callback_data="send_voice")]])
        update.message.reply_text(text=f"*[Бот]:* {assistant_response}", parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e: print(f"Error in generate_chatgpt_response: {e}")


def button_callback(update, context):
    try:
        query = update.callback_query
        chat_id = query.message.chat_id

        if query.data == "send_voice" and chat_id in message_log:
            assistant_response = message_log[chat_id]["assistant_response"]
            voice = TTV(assistant_response)
            context.bot.send_voice(chat_id=chat_id, voice=voice)
            del message_log[chat_id] 
    except Exception as e: print(f"Error in button_callback: {e}")

def voice_message(update, context):
    try:
        voice_file = context.bot.getFile(update.message.voice.file_id)
        voice_file.download("voice_message.ogg")
        audio_clip = AudioFileClip("voice_message.ogg")
        audio_clip.write_audiofile("voice_message.wav", codec="pcm_s16le")
        audio_file = open("voice_message.wav", "rb")
        transcript = openai.Audio.transcribe("whisper-1", audio_file).text
        update.message.reply_text(text=f"*[Вы]:* _{transcript}_", parse_mode=telegram.ParseMode.MARKDOWN)
        simulate_typing_animation(update, context)
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
        message_log[update.effective_chat.id] = {"role": "user", "content": transcript}
        response = openai.ChatCompletion.create(
            model=modeL,
            messages=[message_log[update.effective_chat.id]]
        )
        ChatGPT_reply = response["choices"][0]["message"]["content"]
        message_log[update.effective_chat.id]["assistant_response"] = ChatGPT_reply
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Получить голосовое сообщение", callback_data="send_voice")]])
        update.message.reply_text(text=f"*[Бот]:* {ChatGPT_reply}", parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e: print(f"Error in voice_message: {e}")

try:
    load_dotenv()

    openai.api_key = os.environ.get("OPENAI_API_KEY")
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    modeL = os.environ.get("MODEL")

    message_log = {}

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, generate_chatgpt_response))
    dispatcher.add_handler(MessageHandler(Filters.voice, voice_message))
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    updater.start_polling()
    updater.idle()
except Exception as e: print(f"Error: {e}")
