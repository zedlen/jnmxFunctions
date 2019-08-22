FROM ubuntu:latest
MAINTAINER Luis Melendez "luis_melendez@jnmx.com.ms"
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential cmake
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["main.py"]