# Copyright Minimasoft (c) 2025

from pathlib import Path
from time import sleep
from os import getenv
from requests.auth import HTTPBasicAuth
from utils import http_get, http_put, step


def load_opensearch_data():
    return {
        "url": getenv('OPENSEARCH_URL'),
        "users": {
            "admin": {
                "user": getenv('OPENSEARCH_ADMIN_USER'),
                "password": getenv('OPENSEARCH_ADMIN_PASSWORD'),
            },
            "dashboard": {
                "user": getenv('OPENSEARCH_DASHBOARD_USER'),
                "password": getenv('OPENSEARCH_DASHBOARD_PASSWORD'),
            },
        }
    }


def provision_opensearch(data):
    auth = HTTPBasicAuth(
        data['users']['admin']['user'],
        data['users']['admin']['password']
    )
    list_url = f"{data['url']}_plugins/_security/api/internalusers"

    response = http_get(list_url, auth=auth, verify=False)
    response.raise_for_status()
    users = response.json()
    for user in users:
        print(user)
        print(users[user])
    create_url = f"{list_url}/{data['users']['dashboard']['user']}"
    user_config = {
        "password": data['users']['dashboard']['password']
    }
    response = http_put(create_url, auth=auth, json=user_config, verify=False)
    response.raise_for_status()


def main():
    print("AAAAAA")
    opensearch_data = step("Load opensearch data", load_opensearch_data)
    step("Provision opensearch", lambda: provision_opensearch(opensearch_data))
    sleep(999999999)


if __name__ == "__main__":
    main()
