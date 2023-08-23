# Object Detection Service

## Background

In this project, you'll design, develop and deploy an object detection service that consists of multiple containerized microservices. 

Users send images through an interactive Telegram bot (the bot you've implemented in the Python project), the service detects objects in the image and send the results to the user.

The service consists of 3 microservices: 

- `polybot`: Telegram Bot container.
- `yolo5`: Image prediction container based on the Yolo5 pre-train deep learning model.
- `mongo`: MongoDB cluster to store data.

## Preliminaries

Create a dedicated GitHub repo for the project (or use the same GitHub repo from the previous Python project and utilize your Telegram bot implementation).

## Implementation guidelines

### The `mongo` microservice

MongoDB is a [document](https://www.mongodb.com/document-databases), [NoSQL](https://www.mongodb.com/nosql-explained/nosql-vs-sql) database, offers high availability deployment using multiple replica sets.
**High availability** (HA) indicates a system designed for durability and redundancy.
A **replica set** is a group of MongoDB servers, called nodes, containing an identical copy of the data.
If one of the servers fails, the other two will pick up the load while the crashed one restarts, without any data loss.

Follow the official docs to deploy containerized MongoDB cluster on your local machine. 
Please note that the mongo deployment should be configured **to persist the data that was stored in it**.

https://www.mongodb.com/compatibility/deploying-a-mongodb-cluster-with-docker

Got HA mongo deployment? great, let's move on...

### The `yolo5` microservice

[Yolo5](https://github.com/ultralytics/yolov5) is a state-of-the-art object detection AI model. It is known for its high accuracy object detection in images and videos.
You'll work with a lightweight model that can detect [80 objects](https://github.com/ultralytics/yolov5/blob/master/data/coco128.yaml) while running on your old, poor, CPU machine. 

The service files are under the `docker_project/yolo5` directory. Copy these files to your repo.

#### Develop the app

The `yolo5/app.py` app is a flask based webserver, with a single endpoint `/predict`, which can be used to predict objects in images.  

To use this endpoint, you don't send the image directly in the HTTP request. Instead, you attach a query parameter called `imgName` to the URL (e.g. `localhost:8081/predict?imgName=street.jpeg`), which represents an image name stored in an **S3 bucket**. 
The service downloads this image from the S3 bucket and detect objects in it. 

Take a look on the code, and complete the `# TODO`s. Feel free to change/add any functionality as you wish!

#### Build and run the app

The `yolo5` app can be running only as a Docker container. This is because the app depends on many files that don't exist on your local machine, but do exist in the [`ultralytics/yolov5`](https://hub.docker.com/r/ultralytics/yolov5) base image.

Take a look at the provided `Dockerfile`, it's already implemented for you, no need to touch.

If you run the container on your local machine, you may need to **mount** (as a volume) the directory containing the AWS credentials on your local machine (`$HOME/.aws/credentials`) to allow the container communicate with S3.  

**Note: Never build a docker image with AWS credentials stored in it! Never commit AWS credentials in your source code! Never!**

Once the image was built and run successfully, you can communicate with it directly by:

```bash
curl -X POST localhost:8081/predict?imgName=street.jpeg
```

For example, here is an image and the corresponding results summary:

<img src="../.img/street.jpeg" width="60%">

```json
{
    "prediction_id": "9a95126c-f222-4c34-ada0-8686709f6432",
    "original_img_path": "data/images/street.jpeg",
    "predicted_img_path": "static/data/9a95126c-f222-4c34-ada0-8686709f6432/street.jpeg",
    "labels": [
      {
        "class": "person",
        "cx": 0.0770833,
        "cy": 0.673675,
        "height": 0.0603291,
        "width": 0.0145833
      },
      {
        "class": "traffic light",
        "cx": 0.134375,
        "cy": 0.577697,
        "height": 0.0329068,
        "width": 0.0104167
      },
      {
        "class": "potted plant",
        "cx": 0.984375,
        "cy": 0.778793,
        "height": 0.095064,
        "width": 0.03125
      },
      {
        "class": "stop sign",
        "cx": 0.159896,
        "cy": 0.481718,
        "height": 0.0859232,
        "width": 0.053125
      },
      {
        "class": "car",
        "cx": 0.130208,
        "cy": 0.734918,
        "height": 0.201097,
        "width": 0.108333
      },
      {
        "class": "bus",
        "cx": 0.285417,
        "cy": 0.675503,
        "height": 0.140768,
        "width": 0.0729167
      }
    ],
    "time": 1692016473.2343626
}
```

The model detected a _person_, _traffic light_, _potted plant_, _stop sign_, _car_, and a _bus_. Try it yourself with different images.

### The `polybot` microservice

You can either integrate your bot implementation from the previous Python project, or use the code sample given to you under `docker_project/polybot` directory. 

In case you use the code sample, make sure you have Telegram bot token, and you know how to expose your bot using `ngrok` when running it locally.

In the sample code, under `bot.py` you'll find the class `ObjectDetectionBot` with a `handle_message()` method that handles incoming messages from end-users.
When users send an image to the bot, you have to upload this image to S3 and perform an HTTP request to the `yolo5` service to predict the objects in this image.

Complete the `# TODO`s in `bot.py` to achieve this goal (or implement equivalent steps if you use your own bot implementation).

Here is an end-to-end example of how it may look like when all your microservices are running. Feel free to send the results to the user in any other form.

<img src="../.img/polysample.jpg" width="30%">

## Deploy the service in a single EC2 instance as a Docker Compose project

Create a Docker Compose project in the `docker-compose.yaml` file to provision the service (all 3 microservices) in a single command (`docker compose up`).
Deploy the compose project in a single EC2 instance located in a public subnet.

Deployment notes:

- Don't configure your compose file to build the images. Instead, push the `yolo5` and `polybot` images to DockerHub or an [ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-console.html) repo and use these images. 
- Attach an IAM role with the relevant permissions (e.g. read/write access to S3). Don't manage AWS credentials yourself, and never hard-code AWS credentials in the `docker-compose.yaml` file. 
- Don't hard-code your telegram token in the compose file, this is a sensitive data. [Read here](https://docs.docker.com/compose/use-secrets/) how to provide your compose project this data in a safe way.  
- You should use the instance's **public IP address** as the registered `polybot` app URL in Telegram servers, there is no need to use Ngrok. Read below how to do it.
- Clean from vulnerabilities

Since the IP address may be changed, you should retrieve the public IP dynamically when the app is launched.
This requires some code changes in `polybot/app.py`. As a reminder, the app url is provided to Telegram servers from an environment variable you define:

```python
# line taken from polybot/app.py
TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']
```

Let's modify this code to load the instance's public IP dynamically:

```python
import requests 

# reference https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html
TELEGRAM_APP_URL = requests.get('http://169.254.169.254/latest/meta-data/local-ipv4').text
```

But now a new problem arises. After this code change, the app won't work when running on our local machine, since the `http://169.254.169.254` address can be resolved only from within an EC2 instance (read the reference link to see why). 

Optimally, our apps should work smoothly both locally, when developers test their features, and also on production environment (on EC2 instance in our case), regardless of the context or environment.
To achieve it we follow a very straightforward and common practice in software engineering - treat both cases in the code:

```python
import requests 

if os.environ.get('TELEGRAM_APP_URL'): # if the TELEGRAM_APP_URL env var is defined, use it
    TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']

else:  # otherwiese, load the public ip address dynamically from within an EC2 instance  
    # reference https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html
    TELEGRAM_APP_URL = requests.get('http://169.254.169.254/latest/meta-data/local-ipv4').text
```

Integrate this change in your `polybot/app.py` code.

## Submission

You have to present your work to the course staff, in a **10 minutes demo**. Your presentations would be evaluated according to the below list, in order of priority:

1. Showcasing a live, working demo of your work. Both locally and in the cloud.
2. Demonstrating deep understanding of the system.
3. Applying best practices and clean work.
4. Successful integration of a new feature, idea, or extension. Be creative!


## Good luck
