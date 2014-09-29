# -*- coding: utf-8 -*-
from twitter_secrets import APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
from twython import Twython
import logging

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)


twitter = Twython(APP_KEY, APP_SECRET,
                  OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

twitter.verify_credentials()

def update_status(ja):
    def maketwstr(ja, title_len):
        elipses = ''
        raw_tit = ja.metadata['article-title']
        if len(raw_tit) >= title_len:
            elipses = u'…'
        title = '"' + ja.metadata['article-title'][:title_len] + elipses + '"'
        doiurl = ja.doiurl()
        '''
        try:
            hashtag = '#' + ja.metadata['article-categories'][0].split(' ')[0]
        except:
            hashtag = '#biology'
        '''
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
