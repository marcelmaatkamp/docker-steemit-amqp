#!/usr/bin/python3
from steempersist import SteemPersist
from steemutils import must_vote
import steem
import fakesyslog as syslog

import pika
import json
import os

class AMQP:
    def __init__(self,pers,channel):
        self.pers=pers
        self.channel=channel
    def other(self,time,event):	
        # print(event)
        channel.basic_publish(exchange=os.environ.get('RABBITMQ_EXCHANGE'), routing_key='steemit.'+event['type'], body=json.dumps(event['event']))

keys=os.environ.get('STEEMIT_ACCOUNT_ACTIVE_KEY')
account=os.environ.get('STEEMIT_ACCOUNT_NAME')
friends=[]

connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ.get('RABBITMQ_HOSTNAME')))
channel = connection.channel()

pers = SteemPersist("amqp")
atf = AMQP(pers, channel)
pers.set_handlers(atf)
pers()
