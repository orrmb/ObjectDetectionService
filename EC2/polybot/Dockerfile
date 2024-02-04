FROM python:3.9-slim
RUN pip install --upgrade pip
RUN pip install --upgrade pillow>=10.2.0
RUN apt-get install -y libc-bin=2.36-9+deb12u4
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "app.py"]
