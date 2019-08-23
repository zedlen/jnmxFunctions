FROM python:3.7
MAINTAINER Luis Melendez "luis_melendez@jnmx.com.ms"

RUN apt-get -y update
RUN apt-get install -y --fix-missing \
    build-essential \
    cmake \    
    python3-dev \
    python3-numpy \
    python3-pip    

# Copy local code to the container image.
ENV APP_HOME /app
ENV GOOGLE_APPLICATION_CREDENTIALS $APP_HOME/JurisnovaMX-81533c07499d.json
ENV INSTANCE_CONNECTION_NAME jurisnovamx:us-central1:jurisnova
WORKDIR $APP_HOME
COPY . .

RUN pip3 install -r requirements.txt
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app