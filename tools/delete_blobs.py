from azure.storage.blob import BlobServiceClient

STORAGE_NAME= "falconestorage",
RESULT_CONTAINER_NAME = "archicad-local"

container_name = RESULT_CONTAINER_NAME
connect_str = "DefaultEndpointsProtocol=https;AccountName=falconestorage;AccountKey=xUepXBEtdcKEp74pOfw0iqv6weQmA5YQPsITR7BzmFA4/j/UdFqoKC3Ja0bv4PbxO9HKvwjkZ1PQ3+jC56ezZA==;EndpointSuffix=core.windows.net"

blob_service_client = BlobServiceClient.from_connection_string(connect_str)

container_client = blob_service_client.get_container_client(container_name)


blob_list = container_client.list_blobs()
for blob in blob_list:
    print(blob.name)
    container_client.delete_blob(blob=blob.name)