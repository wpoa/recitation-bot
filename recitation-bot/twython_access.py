from twitter_secrets import APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
from twython import Twython
import logging

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)


twitter = Twython(APP_KEY, APP_SECRET,
                  OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

twitter.verify_credentials()

def update_status(ja):
    def maketwstr(ja, title_len):
        title = '"' + ja.metadata['article-title'][:title_len] + u'…' + '"'
        doiurl = ja.metadata.doiurl()

        twitterstr = '%s uploaded %s #openaccess' % (title, doiurl) 
        return twitterstr
    for title_len in [82, 80, 75, 70, 65, 60, 55, 50, 45, 40]:
        twitterstr = maketwstr(ja, title_len)
        logging.info('twitterstr' + twitterstr)
        try:
            twitter.update_status(status=twitterstr)
            break
        except:
            continue
