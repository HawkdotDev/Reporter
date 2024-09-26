import tweepy
import smtplib
import time
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tweepy import HTTPException, TweepyException
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('twitter_bot.log', mode='a'),
                        logging.StreamHandler()
                    ])

API_KEY = os.getenv('API_KEY')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')

def load_pages_to_monitor():
    with open('pages_to_monitor.json') as f:
        data = json.load(f)
    logging.info("Loaded pages to monitor: %s", data['pages'])
    return data['pages']

auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

tracked_tweet_ids = set()

LIKE_THRESHOLD = 20 
RETWEET_THRESHOLD = 10 

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info(f"Email sent: {subject}")

    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def monitor_pages(pages):
    for page in pages:
        try:
            logging.info(f"Checking tweets from: {page}")
            tweets = api.user_timeline(screen_name=page, count=5, tweet_mode='extended')

            for tweet in tweets:
                if tweet.id not in tracked_tweet_ids:
                    tracked_tweet_ids.add(tweet.id)

                    if tweet.favorite_count >= LIKE_THRESHOLD or tweet.retweet_count >= RETWEET_THRESHOLD:
                        subject = f"New trending tweet from {page}"
                        body = (f"Content: {tweet.full_text}\n"
                                f"Likes: {tweet.favorite_count}\n"
                                f"Retweets: {tweet.retweet_count}\n"
                                f"Link: https://twitter.com/{page}/status/{tweet.id}")
                        send_email(subject, body)
                        logging.info(f"Trending tweet detected and email sent: {tweet.full_text}")
                    else:
                        logging.info(f"No trending activity for tweet: {tweet.full_text}")

        except HTTPException as e:
            if e.response.status_code == 429:
                logging.warning("Rate limit reached, sleeping for 15 minutes.")
            else:
                logging.error(f"Twitter API error: {e}")
        except TweepyException as e:
            logging.error(f"Tweepy error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    pages_to_monitor = load_pages_to_monitor()
    while True:
        try:
            logging.info("Monitoring pages...")
            monitor_pages(pages_to_monitor)
            logging.info("Waiting for the next check...")
            time.sleep(60)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(60)