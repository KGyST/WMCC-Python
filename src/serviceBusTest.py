import datetime
import time
from azure.servicebus import ServiceBusClient
import multiprocessing as mp
from azure.servicebus import QueueClient, Message
import os

connectionstring = 'Endpoint=sb://sb-wmmc-dev.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=PpeIClSmS6S615ul5wv0Nos6+HM2SuJOcbmvbb5afRA='
# sb_client = ServiceBusClient.from_connection_string(connectionstring)
queue_client = QueueClient.from_connection_string(connectionstring, "taskqueue")

def queueReceiver():
    with queue_client.get_receiver() as queue_receiver:
        while True:
            message = queue_receiver.next()
            print(f"{message} received")
            message.complete()


def sender():
    worker = mp.Process(target=queueReceiver)
    worker.start()
    print(worker.pid)
    worker.name = "teszt"
    print(worker.name)

    p = os.popen(f'tasklist /FI "pdi eq {worker.pid}"')
    for l in p.readlines():
        try:
            print(int(l[29:34]))
        except:
            print (l)

    for _i in range(10):
        queue_client.send(Message(str(_i)))
        print(f"{_i} sent")

    print(f'All messages sent')
    # worker.terminate()


if __name__ == '__main__':
    mp.freeze_support()
    sender()
