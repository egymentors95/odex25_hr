import requests
import json
from urllib.parse import urlparse


def is_valid_port(port):
    try:
        port = int(port)
        if 1 <= port <= 65535:
            return True
        else:
            return False
    except Exception:
        return False


def is_valid_ip(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


headers = {'Content-Type': 'application/json'}


class ParsedRequest(object):
    def __init__(self, data):
        self.__dict__ = json.loads(data)

serverIP = "http://160.153.0.122:8008"
loginUrl = serverIP + "/jwt-api-token-auth/"
refreshUrl = serverIP + "/jwt-api-token-refresh/"
employeeUrl = serverIP + "/personnel/api/employee/"
departmentsUrl = serverIP + "/personnel/api/departments/"
terminalsUrl = serverIP + "/iclock/api/terminals/"
areasUrl = serverIP + "/personnel/api/areas/"
positionsUrl = serverIP + "/personnel/api/positions/"
transctionsUrl = serverIP + "/iclock/api/transactions/"
defaultHeaders = {'Content-Type': 'application/json'}


class HttpHelper(object):

    def login(self, username, password, url=loginUrl, headers=defaultHeaders):
        data = {'username': username, 'password': password}
        return requests.post(url, data=json.dumps(data), headers=headers)

    def refresh(self, token, url=refreshUrl, headers=defaultHeaders):
        data = {'token': token}
        return requests.post(url, data=json.dumps(data), headers=headers)

    def fetch_employees(self, data, token, url=employeeUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, data=json.dumps(data), headers=headers)

    def fetch_departments(self, data, token, url=departmentsUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, data=json.dumps(data), headers=headers)

    def fetch_terminals(self, data, token, url=terminalsUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, data=json.dumps(data), headers=headers)

    def fetch_areas(self, data, token, url=areasUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, data=json.dumps(data), headers=headers)

    def fetch_positions(self, data, token, url=positionsUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, data=json.dumps(data), headers=headers)

    def fetch_transctions(self, token, url=transctionsUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, headers=headers)

    def fetch_empl_transctions(self, data, token, url=transctionsUrl):
        headers = {
            'Authorization': 'JWT ' + token,
            'Content-Type': 'application/json'
        }
        return requests.get(url, data=json.dumps(data), headers=headers)


httpHelper = HttpHelper()
