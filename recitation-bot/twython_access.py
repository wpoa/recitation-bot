from twitter_secrets import APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
from twython import Twython
import logging

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)


twitter = Twython(APP_KEY, APP_SECRET,
                  OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

twitter.verify_credentials()

def update_status(ja):
    twitterstr = "#openaccess article uploaded: "
    twitterstr += ja.metadata['article-title'][:75] #Hopefully this will keep it undeer 140 characters but it might not if there's lots of unicode
#    What about trying to determine a hashtag first (default: ' #Biology'), then subtract its length from 86 and shorten the article title to the last word that fits in completely?
#    twitterstr += ja.metadata['hashtag'] 
    twitterstr += ja.urlstr() #Perhaps better use the DOI-based page title here, so that altmetrics can pick it up
    logging.info(twitterstr)
    twitter.update_status(status=twitterstr)
