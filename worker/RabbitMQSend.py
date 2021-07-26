#!/usr/bin/env python
import pika, json

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')

for i in range(10):
    channel.basic_publish(exchange='', routing_key='hello', body= json.dumps({'teszt': 'teszt'}))
print(" [x] Sent 'Hello World!'")
connection.close()