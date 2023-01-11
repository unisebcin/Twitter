import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import pandas as pd
import openpyxl
from http import HTTPStatus
import os
from dotenv import load_dotenv
import logging

load_dotenv('.env')
logger = logging.getLogger('Utils')


class Settings:
    logger.info('Settings class initialized...')

    def __init__(self):
        self.bearer = os.environ.get('bearer')
        if self.bearer:
            logger.info('Twitter bearer found...')
        else:
            logger.warning('Twitter bearer not found!!!')
        self.url_base = "https://api.twitter.com/2/"
        self.auth = {"Authorization": "Bearer " + self.bearer}
        self.start_date = (datetime.utcnow() - relativedelta(days=10)).isoformat().split('T')[0]
        self.today = datetime.utcnow().isoformat().split('T')[0]
        self.username = 'businessline'
        self.save_path_tweets = self.username + '_tweets_' + self.today + '.xlsx'
        self.save_path_likers = self.username + '_likers_' + self.today + '.xlsx'
        self.save_path_retweeters = self.username + '_retweeters_' + self.today + '.xlsx'

    def check_conf(self, user_info: dict):
        logger.info(f'Configuration check for twitter user {self.username}')
        if 'id' not in user_info:
            return {'status': False, 'message': 'User does not exist..! Please check username...'}
        elif user_info['protected']:
            return {'status': False, 'message': 'This is a Twitter protected account. Please retry with a public '
                                                'account.'}
        return {'status': True, 'message': 'success'}


def get_user_info(api: Settings):
    logger.info('Retrieving User Info')
    info = []

    url_info = api.url_base + f"users/by/username/{api.username}"
    params = {
        'user.fields': 'created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld'
    }
    resp = requests.get(url_info, headers=api.auth, params=params)
    if resp and 'data' in resp.json():
        info = resp.json()['data']
    elif resp.status_code == HTTPStatus.UNAUTHORIZED:
        raise ValueError('User is not authorized! Please check your bearer token...')
    return info


def get_user_tweets(user_info: dict, api: Settings):
    logger.info('Retrieving User Tweets')
    user_id = user_info['id']
    start_date = datetime.fromisoformat(api.start_date)

    info = []
    url_tweets = api.url_base + f"users/{user_id}/tweets"
    params = {
        'max_results': 100,
        'start_time': start_date.isoformat('T') + 'Z',
        'tweet.fields': 'author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings,source,text',
        'user.fields': 'created_at,description,entities,id,location,name,protected,public_metrics,username'
    }
    resp = requests.get(url_tweets, headers=api.auth, params=params)
    if resp.status_code != HTTPStatus.OK:
        n = 0
        while n < 6:
            n += 1
            print(
                f"""Stand by for 5 min. ({n}/6) due to twitter rate limits (tweet timeline)...
                If error remains after 30 min, please wait for at least 2 hrs and then try again.
""")
            time.sleep(300)
            resp = requests.get(url_tweets, headers=api.auth, params=params)
            if resp.status_code == HTTPStatus.OK:
                break
    if resp and 'data' in resp.json():
        info = resp.json()['data']
        while 'next_token' in resp.json()['meta']:
            params['pagination_token'] = resp.json()['meta']['next_token']
            resp = requests.get(url_tweets, headers=api.auth, params=params)
            if resp and 'data' in resp.json():
                info.extend(resp.json()['data'])
            elif resp.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                n = 0
                while n < 5:
                    n += 1
                    print(
                        f'Stand by for 5 min. ({n}/6)\nThis may go up to 15 min due to twitter rate limits...')
                    time.sleep(300)
                    resp = requests.get(url_tweets, headers=api.auth, params=params)
                    if resp.status_code == HTTPStatus.OK:
                        info.extend(resp.json()['data'])
                        break
            else:
                break
    return info


def save_to_file(data_type: str, data: list, api: Settings):
    logger.info(f'Saving File : {data_type}')
    if data_type == 'tweets':
        plist = []
        for tweet in data:
            id = tweet['id']
            url = f"https://twitter.com/{api.username}/status/" + tweet['id']
            day = tweet['created_at'].split('T')[0]
            likes = tweet['public_metrics']['like_count']
            retweets = tweet['public_metrics']['retweet_count']
            replies = tweet['public_metrics']['reply_count']
            text = tweet['text']
            plist.append((id, url, day, likes, retweets, replies, text))
        columns = ['Tweet ID', 'Tweet URL', 'Date', 'Likes Count', 'Retweet Count', 'Reply Count',
                   'Comment']
        path = api.save_path_tweets
    else:
        plist = []
        for item in data:
            userid = item['id']
            username = item['username']
            name = item['name']
            user_followers = item['public_metrics']['followers_count']
            user_following = item['public_metrics']['following_count']
            user_tweets = item['public_metrics']['tweet_count']
            user_description = item['description']
            plist.append((userid, name, username, user_description, user_followers, user_following, user_tweets))

        columns = ['User ID', 'Name', 'Username', 'Description', 'Followers Count', 'Following Count',
                   'Tweets Count']
        if data_type == 'likers':
            path = api.save_path_likers
        else:
            path = api.save_path_retweeters

    data = pd.DataFrame(plist, columns=columns)
    data.drop_duplicates(keep='first', inplace=True)
    data.to_excel(path, index=False)
    return len(data)


def get_likers_retweeters(requestType: str, tweet: dict, api: Settings):
    logger.info('Retrieving Tweet Likers-Retweeters')
    idx = tweet['id']
    data = []
    if requestType == 'likers':
        count = tweet['public_metrics']['like_count']
        url = api.url_base + f"tweets/{idx}/liking_users"
    else:
        count = tweet['public_metrics']['retweet_count']
        url = api.url_base + f"tweets/{idx}/retweeted_by"

    params = {"user.fields": "id,name,username,description,public_metrics"}
    resp = requests.get(url, headers=api.auth, params=params)
    if resp.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        n = 0
        while n < 5:
            n += 1
            print(
                f'Stand by for 5 min. ({n}/6)\nThis may go up to 15 min due to twitter rate limits...')
            time.sleep(300)
            resp = requests.get(url, headers=api.auth, params=params)
            if resp.status_code == HTTPStatus.OK:
                break
    if resp and 'data' in resp.json():
        data = resp.json()['data']
        while 'next_token' in resp.json()['meta'] and count > 99:
            params["pagination_token"] = resp.json()['meta']['next_token']
            resp = requests.get(url, headers=api.auth, params=params)
            if resp and 'data' in resp.json():
                data.extend(resp.json()['data'])
            elif resp.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                n = 0
                while n < 5:
                    n += 1
                    print(
                        f'Stand by for 5 min. ({n}/6)\nThis may go up to 15 min due to twitter rate limits...')
                    time.sleep(300)
                    resp = requests.get(url, headers=api.auth, params=params)
                    if resp.status_code == HTTPStatus.OK:
                        data.extend(resp.json()['data'])
                        break
            else:
                break
    return {'status': resp.status_code, 'data': data}
