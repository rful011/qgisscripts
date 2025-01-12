import sys

sys.path.append('..')
import pyepicollect as pyep
import logging
import pprint
import requests

pp = pprint.PrettyPrinter(indent=2)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
BASE_URL = "https://five.epicollect.net/api/"  # oauth/token"

def api_request(api, data):
    url = BASE_URL + api
    logger.debug("Request URL: %s", url)
    logger.debug("Request data: %s", pprint.pformat(data))

    response = requests.post(url, data=data)

    if response.status_code == 200:
        return response.json()

    logger.error("Failed to obtain token. Response details: %s", pprint.pformat(response.json()))
    return None

def request_token(client_id, client_secret):
    "" Get token. Each token is valid for 2 hours

    :param client_id: The client ID for authentication
    :param client_secret: The client secret for authentication
    :return: A dictionary with the token information or error details
    ""
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }

    return api_request('oauth/token', data)
"""

if  len(sys.argv) > 1:
    p_name = sys.argv[1]
else:
    p_name = input('project name:')

projects = {
    'Tiriweeds':{
        'name': 'Tiritiri Matangi Island weed reports',
        'client': '5891',
        "slug": 'tiritiri-matangi-island-weed-reports',
        'secret': 'xCP4UWTMVAiX6l7v0oIYrb9FmP9mLfF2CHA7dq1F'
    },
    'Tiriweeds-old': {
        'name': 'Tiriweeds',
        'client': '5889',
        "slug": 'tiriweeds',
        'secret': 'tUoMFS3ARj2rl3vvDUDgxGuExRwijrWHmQFzjgrH'
    }
}

if not projects.get(p_name):
    print(f"no project: '{p_name}'")
    sys.exit(1)

conf = projects[p_name]

token = pyep.auth.request_token(conf['client'], conf['secret'])

project = pyep.api.get_project(conf['slug'], token['access_token'])
pprint.pp(project)

print("getting entries:")

entries = pyep.api.get_entries(conf['slug'], token['access_token'])

print(f"number of entries: {len(entries['data']['entries'])}")
#pprint.pp(entries['data']['entries'])

#    name, description, created, source, classification, rw_id, type
waypoints = []

for entry in entries['data']['entries']:
    wp = {}
    wp['name'] = "FW "


