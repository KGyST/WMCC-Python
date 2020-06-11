import time
from azure.servicebus import QueueClient, Message

connectionstring = 'Endpoint=sb://sb-wmmc-dev.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=PpeIClSmS6S615ul5wv0Nos6+HM2SuJOcbmvbb5afRA='

queue_client = QueueClient.from_connection_string(connectionstring, "taskqueue")

# Receive the message from the queue
with queue_client.get_receiver() as queue_receiver:
    while True:
        messages = queue_receiver.fetch_next(timeout=3)
        for message in messages:
            print(message)
            time.sleep(1)
            message.complete()