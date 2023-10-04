import requests
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
import boto3
from pymongo import MongoClient
from collections import Counter
import pymongo



class Bot:

    def __init__(self, token, telegram_chat_url,cert_ssl):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)
        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/',certificate=open(cert_ssl, 'r'), timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class ObjectDetectionBot(Bot):

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if self.is_current_msg_photo(msg):
            images_bucket = os.environ['BUCKET_NAME']
            s3 = boto3.client('s3', region_name='us-west-2')
            photo_path = self.download_user_photo(msg)
            img_name = self.download_user_photo(msg).split('/')[1]
            self.telegram_bot_client.send_message(msg['chat']['id'], text='A few moment')
            s3.upload_file(photo_path, images_bucket, f'Images/{img_name}')
            post = requests.post(url=f'http://yolo-app:8081/predict?imgName={img_name}')
            try:
                cluster_uri = "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=myReplicaSet"
                myclient = MongoClient(cluster_uri)
                logger.info("Good Connection")
                mydb = myclient["mydatabase"]
                mycol = mydb["images_predict"]
                cur = mycol.find({})
                documents = []
                for document in cur:
                    documents.append(document)
                myclient.close()
            except pymongo.errors.ServerSelectionTimeoutError:
                logger.info("Error Connection")

            object=[]
            for x in document['labels']:
                object.append(x['class'])
            object_counts = Counter(object)
            ans = ','.join([f'\n{obj}: {count}' for obj, count in object_counts.items()])
            logger.info(object_counts)
            sums = sum(object_counts.values())
            self.telegram_bot_client.send_message(msg['chat']['id'], text= f'There {sums} Object in Picture : {ans}\n Thank you!')
        elif msg['text'] == '/end':
            self.telegram_bot_client.send_message(msg['chat']['id'], text='Thank you and never come back!!!')
            time.sleep(2)
            self.telegram_bot_client.send_message(msg['chat']['id'], text='Hey, I`m Kidding, I`m here for you, come back whenever you want ')
        elif msg['text'] == '/help':
            self.telegram_bot_client.send_message(msg['chat']['id'], text='I am base on Yolo5 object detection AI model. It is known for its high accuracy object detection in images and videos, I can detect 80 objects.\n Try me!\n Send me a Photo like the example below')
            self.telegram_bot_client.send_video(msg['chat']['id'], video=open('helpVideo.mp4', 'rb'), supports_streaming=True)
        elif msg['text'] == '/start':
            self.telegram_bot_client.send_message(msg['chat']['id'], text='Hi, my name is Yolobot.\nPlease send me a photo and I will try to predict the objects in your image')



