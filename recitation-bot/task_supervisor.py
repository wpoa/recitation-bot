# -*- coding: utf-8 -*-

from journal_article import journal_article
from detect_in_use_dois import doi_finder
import os
import pywikibot
import shelve
import threading
from collections import deque
import time
import json
from sys import stderr
import logging

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)

faillog = logging.getLogger('faillog')
failhandler = logging.FileHandler('/data/project/recitation-bot/public_html/faillog.html')
failhandler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
faillog.addHandler(failhandler)

'''For every DOI-article pair in existence it can be one of the following statuses to us:
1. previously_done #we've already processed it
2. in_progress #it's in our queue to do
3. not_doing #we've manually specified not to do this pair
4. new_additions #the doi is in use on wikipedia and we have to detect it
'''

def add_jumpers_to_deque(article_deque):
    logging.debug('jumpers thread launched')
    while 1: # True
        jumpers_file_name = '/data/project/recitation-bot/recitation-bot/jump_the_queue.log'
        jumpers_file = open(jumpers_file_name,'r')
        jumpers_contents = jumpers_file.read()
        jumpers_file.close()
        open(jumpers_file_name,'w').close() #blank the file
	jumper_lines = jumpers_contents.split('\n')
        jumper_lines = jumper_lines[:-1]#-1 because there will always be an empty line due to the way of splitting
        logging.info('%s items found from the jumper queue', len(jumper_lines)) 
        for doi_input in jumper_lines:
            if doi_input: # check for empty strings
                doi, reupload_text = doi_input.split('\t')
                reupload = True if reupload_text == 'reupload_on' else False 
                article_deque.append({'doi':doi,'reupload':reupload,'article':None})
        time.sleep(10)

def add_detected_to_deque(article_deque):
    logging.debug('detector thread launched')
    finder = doi_finder(lang='test2wiki')
    finder.find_new_doi_article_pairs(article_deque)

def report_status(doi, status, success):
    success_str = 'succeeded' if success else 'failed'
    waiting_page_path = '/data/project/recitation-bot/public_html/'+doi+'.html'
    waiting_page = open(waiting_page_path, 'w')
    waiting_text = r'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<title>DOI upload status report</title>
<html>
<body>
<p>doi: %s</p>
<p>success: %s </p>
<p>%s</p>
</body>
</html>''' % (doi, success_str, status)
    waiting_page.write(waiting_text.encode('utf-8'))
    waiting_page.close()

    #log off all the failures
    if not success:
        logging.info('DOI: %s \nFAIL MESSAGE:%s' % (doi, status) )
        faillog.info('DOI: %s \nFAIL MESSAGE:%s \n\n' % (doi, status) )



def convert_and_upload(article_deque):
    # creates shelf store for article data (history)
    shelf = shelve.open('journal_shelf', writeback=False)

    # parameters as key-value pairs, used like static variables
    parameters = {
        "data_dir" : '/data/project/recitation-bot/recitation-bot/data',
        "jats2mw_xsl" : '/data/project/recitation-bot/JATS-to-Mediawiki/jats-to-mediawiki.xsl',
        "wikisource_site" : 'en',
        "wikisource_basepath" : 'Wikisource:WikiProject_Open_Access/Programmatic_import_from_PubMed_Central/',
        "image_extensions": ['jpg', 'jpeg', 'png']
    }

    # main loop
    while 1: # True
        try:
            doi_article = article_deque.pop()
            doi = doi_article['doi']
            reupload = doi_article['reupload']
            logging.info('working on doi %s and reupload was %s' % (str(doi), str(reupload)))
            article = doi_article['article']
            logging.debug('associated article %s' % article)
            if doi not in shelf.keys() or reupload:
                logging.info('doi %s was not in shelf' % doi)
                try:
                    ja = journal_article(doi=doi, article=article, parameters=parameters)
                    ja.get_pmcid()
                    ja.get_targz()
                    ja.extract_targz()
                    ja.find_nxml()
                    ja.extract_metadata()
                    ja.xslt_it()
                    ja.upload_images()
                    ja.get_mwtext_element()
                    ja.replace_image_names_in_wikitext()
                    ja.push_to_wikisource()
                    ja.push_redirect_wikisource()            
                    shelf[doi] = ja
                    shelf.sync()
                    report_status(doi, ja.htmlstr(), success=True)
                except Exception as e:
                    logging.exception(e)
                    logging.debug(e)
                    report_status(doi, str(e), success=False)
            else:
                logging.info('doi %s was in shelf' % doi)
        except IndexError: #nothing in the deque
            logging.info('nothing in deque sleepytime')
            time.sleep(10)
            continue
    shelf.close()

article_deque = deque()
jump_producer = threading.Thread(target=add_jumpers_to_deque, kwargs={'article_deque':article_deque})
detect_producer = threading.Thread(target=add_detected_to_deque, kwargs={'article_deque':article_deque})
consumer = threading.Thread(target=convert_and_upload, kwargs={'article_deque':article_deque})

jump_producer.start()
detect_producer.start()
consumer.start()
logging.debug('all threads started')

jump_producer.join()
detect_producer.join()
consumer.join()
print('finished') #this should never be reached if all loops are suffiicently infinite.
