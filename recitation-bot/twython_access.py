from twitter_secrets import APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
from twython import Twython
import logging

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)


twitter = Twython(APP_KEY, APP_SECRET,
                  OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

twitter.verify_credentials()

def update_status(ja):
    twitterstr = "Open Access article: "
    twitterstr += ja.metadata['article-title'][:75] #Hopefully this will keep it undeer 140 characters but it might not if there's lots of unicode
    twitterstr += "... uploaded. " 
    twitterstr += ja.urlstr()
    logging.info(twitterstr)
    twitter.update_status(status=twitterstr)
