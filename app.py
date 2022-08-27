#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
"""

import logging, os, asyncio, io, warnings, datetime
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from deepgram import Deepgram
from stability_sdk import client
from PIL import Image
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

load_dotenv()
dg_client = Deepgram(os.getenv('DEEPGRAM_API'))
stability_client = client.StabilityInference(key=os.getenv('STABILITY_API'))

# Enable logging
logging.basicConfig(filename='log.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filemode='a', level=logging.INFO)
logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def text (update, context):
    """Echo the user message."""
    update.message.reply_text('This bot only works with audio recordings. Hold down the microphone button to record audio.')

def voice(update, context):
    '''Parse audio recording'''
    # https://docs.python-telegram-bot.org/en/stable/telegram.message.html?highlight=reply_text#telegram.Message.reply_text
    # Get audio file
    audio_file = context.bot.get_file(update.message.voice.file_id)
    audio_file.download(f"voice_note.ogg")
    update.message.reply_text('Recording received, image available shortly.')

    # Get transcript
    async def test():
        with open('voice_note.ogg', 'rb') as audio:
            source = {'buffer': audio, 'mimetype': 'audio/ogg'}
            response = await dg_client.transcription.prerecorded(source, {'punctuate': True})
        return response
    response = asyncio.run(test())
    transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
    logger.info(transcript)

    # Generate image
    answers = stability_client.generate(prompt=transcript)
    for resp in answers:
        for artifact in resp.artifacts:
            if artifact.finish_reason == generation.FILTER:
                warnings.warn('BOOOOO')
            if artifact.type == generation.ARTIFACT_IMAGE:
                img = Image.open(io.BytesIO(artifact.binary))
                img.save(f'image_{datetime.datetime.now().timestamp()}.png')
                img.save('image.png')

    # Return generated image
    update.message.reply_photo(open('image.png', 'rb'), caption=transcript)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(os.getenv('TELEGRAM'), use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))

    # on noncommand i.e message
    dp.add_handler(MessageHandler(Filters.text, text))
    dp.add_handler(MessageHandler(Filters.voice, voice))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()