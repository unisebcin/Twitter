import requests
import time     # noqa: F401
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv('.env')


stream_rules_url = 'https://api.twitter.com/2/tweets/search/stream/rules'
stream_url = 'https://api.twitter.com/2/tweets/search/stream'
headers = {"Authorization": "Bearer " + os.environ.get('bearer')}
logger = logging.getLogger('Stream')


def add_rule(value: str, tag: str):
    logger.info('New rule to be added')
    """
    :param value: has to be iat twitter building rules conf.
            Exp: {"value": "bio_location:nyc"} or {"value": "@businessline",}
    :param tag: any name to be given for rule added.
    :return: response of twitter add rule end point
    """
    rule_json = {"add": [{"value": value, "tag": tag}]}
    return requests.post(stream_rules_url, headers=headers, json=rule_json).json()


def get_rules():
    logger.info('All rule to be retrieved')
    return requests.get(stream_rules_url, headers=headers).json()


def delete_rules(ids: list):
    logger.info('Rule to be deleted')
    rules_delete_json = {
        "delete": {
            "ids": ids
        }
    }
    return requests.post(stream_rules_url, headers=headers, json=rules_delete_json).json()


def start_stream():
    logger.info('Streaming...')
    s = requests.Session()
    counter = 0
    with s.get(stream_url, headers=headers, stream=True) as resp:
        for line in resp.iter_lines():
            if line:
                try:
                    my_json = line.decode('utf8').replace("'", '"')
                    data = json.loads(my_json)
                    logger.info(data)
                except Exception:
                    counter += 1
                    if counter == 3:
                        return
                    logger.exception('Error : ')
                    logger.warning(line)


if __name__ == '__main__':
    while True:
        logger.info('Infinite loop is about to start...')
        start_stream()
        logger.warning('Connection Lost: Sleeping for 2 min...')
        break
        # time.sleep(120)
