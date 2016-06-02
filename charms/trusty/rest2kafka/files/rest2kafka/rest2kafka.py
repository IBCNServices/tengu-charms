#!/usr/bin/python
#pylint: disable=c0111,c0103
# Full docs pykafka: https://pykafka.readthedocs.io/en/latest/
# Full docs Flask: http://flask.pocoo.org/
# Installation
# sudo apt-get install python-pip python-dev
# sudo pip2 install pykafka Flask
import os

from pykafka import KafkaClient
from flask import Flask, request, Response

kafka_connect_path = os.path.realpath(os.path.dirname(__file__) + '/etc/kafka.connect')
with open(kafka_connect_path, "r") as connect_file:
    KAFKA_CONNECT = connect_file.read()

APP = Flask(__name__)

@APP.route("/")
def hello():
    return "REST to kafka v0.0.1"

@APP.route("/<topic>", methods=['GET'])
def get_topic(topic):
    client = KafkaClient(hosts=KAFKA_CONNECT)
    intopic = client.topics[topic.encode('UTF-8')]
    consumer = intopic.get_simple_consumer(consumer_timeout_ms=1000)
    text = ''
    for message in consumer:
        if message is not None:
            text = text + "{}: {}\n".format(message.offset, message.value)
    return Response(
        text,
        status=200,
        mimetype='text/plain',
    )


@APP.route("/<topic>", methods=['POST'])
def POST_topic(topic):
    client = KafkaClient(hosts=KAFKA_CONNECT)
    topic = client.topics[topic.encode('UTF-8')]
    with topic.get_sync_producer() as producer:
        producer.produce(request.data)
    return Response(
        "Data written to topic",
        status=200,
        mimetype='text/plain',
    )

if __name__ == "__main__":
    DEBUG = (os.environ.get('DEBUG', 'False').lower() == 'true')
    APP.run(host='0.0.0.0', debug=DEBUG, threaded=True)
