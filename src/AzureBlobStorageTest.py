import os, uuid
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__

# Create a blob client using the local file name as the name for the blob
container_name = "archicad-dev"
connect_str = "DefaultEndpointsProtocol=https;AccountName=falconestorage;AccountKey=xUepXBEtdcKEp74pOfw0iqv6weQmA5YQPsITR7BzmFA4/j/UdFqoKC3Ja0bv4PbxO9HKvwjkZ1PQ3+jC56ezZA==;EndpointSuffix=core.windows.net"
local_file_name = "ARCHICAD data schema.json"

print("\nListing blobs...")

# List the blobs in the container
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_client = blob_service_client.get_container_client(container_name)
# blob_client = blob_service_client.get_blob_client(container=container_name, blob=local_file_name)
# with open(local_file_name, "rb") as data:
#     blob_client.upload_blob(data)


blob_list = container_client.list_blobs()
for blob in blob_list:
    print("\t" + blob.name)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob)
    blob_client.delete_blob()


# print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)
#
# # Upload the created file
# with open(local_file_name, "rb") as data:
#     blob_client.upload_blob(data)