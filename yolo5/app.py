import json
import time
from pathlib import Path
import pymongo
import requests
from flask import Flask, request
from detect import run
import uuid
import yaml
from loguru import logger
import os
import boto3
from pymongo import MongoClient


images_bucket = os.environ['BUCKET_NAME']

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    # Generates a UUID for this current prediction HTTP request. This id can be used as a reference in logs to identify and track individual prediction requests.
    prediction_id = str(uuid.uuid4())

    logger.info(f'prediction: {prediction_id}. start processing')

    # Receives a URL parameter representing the image to download from S3
    img_name = request.args.get('imgName')
    original_img_path = f'Image/{img_name}'

    s3 = boto3.client('s3', region_name='us-west-2')
    s3.download_file(images_bucket, f'Images/{img_name}', original_img_path)
    logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')


    # Predicts the objects in the image
    run(
        weights='yolov5s.pt',
        data='data/coco128.yaml',
        project='static/data',
        name=prediction_id,
        source=original_img_path,
        save_txt=True
    )

    logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

    # This is the path for the predicted image with labels
    # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.
    predicted_img_path = Path(f'static/data/{prediction_id}/{img_name}')

    s3.upload_file(f'static/data/{prediction_id}/{img_name}', images_bucket, f'Images-predicted/predict_{img_name}')
    logger.info(f'Upload image to S3 bucket {images_bucket}')
    # Parse prediction labels and create a summary
    pred_summary_path = Path(f'static/data/{prediction_id}/labels/{img_name.split(".")[0]}.txt')
    logger.info(type(pred_summary_path))
    if pred_summary_path.exists():
        with open(pred_summary_path) as f:
            labels = f.read().splitlines()
            labels = [line.split(' ') for line in labels]
            labels = [{
                'class': names[int(l[0])],
                'cx': float(l[1]),
                'cy': float(l[2]),
                'width': float(l[3]),
                'height': float(l[4]),
            } for l in labels]

        logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

        prediction_summary = {
            'prediction_id': prediction_id,
            'original_img_path': str(original_img_path),
            'predicted_img_path': str(predicted_img_path),
            'labels': labels,
            'time': time.time()
        }

        cluster_uri = "mongodb://mongo1:27017,mongo2:27018,mongo3:27019/?replicaSet=myReplicaSet"
        myclient = MongoClient(cluster_uri)
        logger.info("Good Connection")
        # Access the database and collection
        mydb = myclient["mydatabase"]
        mycol = mydb["images_predict"]
        x = mycol.insert_one(prediction_summary)
        myclient.close()
        logger.info("Send Data to MongoDB")
        return json.dumps(prediction_summary ,default=str,  indent=4)
    else:
        return f'prediction: {prediction_id}/{original_img_path}. prediction result not found', 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081, debug=True)
