"""Module used to manage aisreceiver service"""
from time import sleep

from .models import Message


def start():
    while True:
        print('Current messages in db:', Message.objects.count())
        sleep(1)
