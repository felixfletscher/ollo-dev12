# -*- coding: utf-8 -*-
import json
import logging

import requests

_logger = logging.getLogger(__name__)


def set_mollie_header(key):
    return {
        'Authorization': 'Bearer ' + str(key),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def send_mollie_request(url, mollie_key, data=None, r_type='post', limit=50):
    """
        get response from the mollie api
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
