# -*- coding: utf-8 -*-
import json
import logging

import requests

_logger = logging.getLogger(__name__)


def set_mollie_header(key):
    """
    Creates a dictionary of request headers for making a request to the Mollie API, including the API key.

    Parameters:
    - key (str): the Mollie API key

    Returns:
    - dict: a dictionary of request headers
    """
    return {
        'Authorization': 'Bearer ' + str(key),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def send_mollie_request(url, mollie_key, data=None, r_type='post', limit=50):
    """
      Makes a request to the Mollie API at the specified URL with the provided data and request type.
      The Mollie API key is passed in the request headers.

      Parameters:
      - url (str): the URL for the Mollie API request
      - mollie_key (str): the Mollie API key
      - data (dict): the data to be included in the request (optional)
      - r_type (str): the type of request (either 'post' or 'patch'; default is 'post')
      - limit (int): the maximum number of items to include in the response (optional)

      Returns:
      - dict: a dictionary containing the response status, data, and status code
      """
    if not url:
        return {}
    headers = set_mollie_header(mollie_key)
    try:
        if data and r_type == 'post':
            response = requests.post(url, data=data, headers=headers)
        elif data and r_type == 'patch':
            response = requests.patch(url, data=data, headers=headers)
        else:
            get_url = f'{url.replace(",","")}?limit={limit}'
            response = requests.get(get_url, headers=headers)
        if response.status_code in (200, 201):
            response_data = response.content.decode()
            return {
                'status': 'successful',
                'data': json.loads(response_data), 'status_code': response.status_code
            }
        elif response.status_code in (404, 500):
            response_data = response.content.decode()
            return {'status': 'error', 'message': json.loads(response_data), 'status_code': response.status_code}
        else:
            return {'status': 'error', 'message': response.content, 'status_code': False}
    except requests.exceptions.RequestException as req_e:
        return {'status': 'error', 'message': str(req_e), 'status_code': False}
