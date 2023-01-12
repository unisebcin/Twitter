from utils import get_user_info, get_user_tweets, save_to_file, get_likers_retweeters, Settings
from http import HTTPStatus
import logging.config
import click
import streamer

logging.config.fileConfig(fname='./app/log.conf', disable_existing_loggers=False)

logger = logging.getLogger('Twitter')


@click.command()
@click.option('--option', default='user_details', help='type of usage, user_details or stream')
def main(option: str):
    if option == 'user_details':
        logger.info('Twitter started')
        api = Settings()

        user_info = get_user_info(api=api)
        config = api.check_conf(user_info)
        if not config['status']:
            logger.error(f"Error : {config['message']}")
            raise ValueError(config['message'])
        logger.info('User info taken')

        user_tweets = get_user_tweets(user_info=user_info, api=api)
        tweet_count = save_to_file(data_type='tweets', data=user_tweets, api=api)
        logger.info('User tweets taken')

        likers = []
        retweeters = []
        counter = 0
        for tweet in user_tweets:
            counter += 1
            # Below lines added iot avoid rate limits and have to be removed before deployment.
            if counter > 7:
                break
            print(f'# of tweets processed : {counter}/{tweet_count}')
            if tweet['public_metrics']['like_count']:
                new_likes = get_likers_retweeters(requestType='likers', tweet=tweet, api=api)
                if new_likes['status'] == HTTPStatus.OK:
                    likers.extend(new_likes['data'])
                else:
                    print('Error!!', new_likes['status'])

            if tweet['public_metrics']['retweet_count']:
                new_retweets = get_likers_retweeters(requestType='retweeters', tweet=tweet, api=api)
                if new_retweets['status'] == HTTPStatus.OK:
                    retweeters.extend(new_retweets['data'])
                else:
                    print('Error!!', new_retweets['status'])

        likers_count = save_to_file(data_type='likers', data=likers, api=api)
        retweeters_count = save_to_file(data_type='retweeters', data=retweeters, api=api)
        logger.info(f'User likers and retweeters taken: tweets : {tweet_count} / Likers : {likers_count} '
                    f'/ Retweeters : {retweeters_count}')

        print(f"""\n ========== SUMMARY =============
        # of tweets retrieved from {api.username} : {tweet_count}
        # of distinct likers retrieved : {likers_count}
        # of distinct retweeters retrieved : {retweeters_count}
        """)
    elif option == 'stream':
        streamer.start_stream()


if __name__ == '__main__':
    main(option='stream')
