import os

from google.cloud import secretmanager


def get_secret_string(secret_name: str, project_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    request = {
        "name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    }
    response = client.access_secret_version(request)
    return response.payload.data.decode("UTF-8")
