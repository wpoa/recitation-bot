import MySQLdb
import datetime
import shelve
import time

import logging
logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)

'''
A doi_finder object connects to the Wikipedia Replica (MySQL) database,
provides methods to get lists of DOI-article pairs including filters for
relevant DOI-article pairs since the last check.
'''
class doi_finder():

    # Connect to database and shelf
    def __init__(self, lang):
        #@TODO make this languag agnostic
        logging.debug('querying on lang: %s',lang)
        host = lang+'.labsdb'
        db = lang+'_p'
        self.conn = MySQLdb.connect(host=host, db=db, port=3306, read_default_file='~/replica.my.cnf')
        self.cursor = self.conn.cursor()        
        #shelf is keyed by doi, and values is a list of pages they appear on
        self.shelf = shelve.open('doi_detector_shelf', writeback=False)
        self.check_time = None

    # Get list of DOIs added since the last check_time
    def get_doi_list(self):
        # namespace difference qstring = u'''select page_title, el_to from externallinks left join page on page_id = el_from where page_namespace = 0 and el_index like 'http://org.doi.dx%' '''
        qstring = u'''select page_title, el_to from externallinks left join page on page_id = el_from where el_index like 'http://org.doi.dx%' '''
        if self.check_time:
            print self.check_time
            qstring += u'''and page_touched > '''
            qstring += self.check_time

        qstring += u''';'''
        uqstring = qstring.encode('utf-8')

        self.cursor.execute(uqstring)
        return self.cursor.fetchall()

    # Find when an article has a new citation with a DOI
    # Update the shelf with new DOI citations
    def find_new_doi_article_pairs(self, article_deque):
        while 1: # True
            curr = self.get_doi_list()
            new_additions = list()
            logging.info('sql query returned %s items', len(curr))
            curr = curr[:100]
            for title, doi_str in curr:
                try:
                    doi = doi_str.split('http://dx.doi.org/')[1]
                except IndexError:
                    continue
                doi_article = {'doi':doi,'article':title}
                if doi not in self.shelf.keys():
                    self.shelf[doi] = [title]
                    new_additions.append(doi_article)
                else:
                    title_list = self.shelf[doi]
                    if title not in title_list:
                        title_list.append(title)
                        self.shelf[doi] = title_list
                        new_additions.append(doi_article)
            utc = datetime.datetime.utcnow()
            self.check_time = utc.strftime('%Y%m%d%H%M%S')
            number_of_new_additions = len(new_additions)
            logging.info('found %s new additions:', number_of_new_additions)
            if new_additions:
                self.article_deque.extendleft(new_addition)
                self.shelf.sync()
            else:
                time.sleep(10)

if __name__ == '__main__':
    from collections import deque
    d = deque()
    getter = doi_finder(lang='enwiki')
    getter.find_new_doi_article_pairs(article_deque)
