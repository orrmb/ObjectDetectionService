import telebot
import flask
from flask import request
import os
from bot import ObjectDetectionBot
from loguru import logger
import requests

with open('/run/secrets/telegram_token', 'r') as file:
    TELEGRAM_TOKEN = file.read().strip()

WEBHOOK_HOST = requests.get('http://169.254.169.254/latest/meta-data/public-ipv4').text
WEBHOOK_PORT = 8443
WEBHOOK_LISTEN = '0.0.0.0'

WEBHOOK_SSL_CERT='./certificates/webhook_cert.pem'
WEBHOOK_SSL_PRIV='./certificates/webhook_pkey.pem'

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (TELEGRAM_TOKEN)

app = flask.Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'OK'


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
        req = request.get_json()
        bot.handle_message(req['message'])
        return 'OK'


if __name__ == "__main__":

    bot = ObjectDetectionBot(TELEGRAM_TOKEN,WEBHOOK_URL_BASE, WEBHOOK_SSL_CERT)
    # Flask with https
    app.run(host='0.0.0.0', port=WEBHOOK_PORT,
       ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
       debug=True)

