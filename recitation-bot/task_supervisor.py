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

'''For every DOI-article pair in existence it can be one of the following statuses to us:
1. previously_done #we've already processed it
2. in_progress #it's in our queue to do
3. not_doing #we've manually specified not to do this pair
4. new_additions #the doi is in use on wikipedia and we have to detect it
'''

def add_jumpers_to_deque(article_deque):
    while 1: # True
        jumpers_file_name = '/data/project/recitation-bot/recitation-bot/jump_the_queue.log'
        jumpers_file = open(jumpers_file_name,'r')
        jumpers_contents = jumpers_file.read()
        jumpers_file.close()
        open(jumpers_file_name,'w').close() #blank the file
        for doi_input in jumpers_contents.split('\n'):
            if doi_input: # check for empty strings
                article_deque.append({'doi':doi_input,'article':None})
        time.sleep(1)

def add_detected_to_deque(article_deque):
	finder = doi_finder(lang='test2wiki', article_deque=article_deque)
	finder.run_in_loop()

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
            article = doi_article['article']
            if doi not in shelf.keys():
                stderr.write(doi)
                #until we can get xslt working
                '''
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
                '''
        except IndexError: #nothing in the deque
            stderr.write('sleep')
            time.sleep(5)
    shelf.close()

article_deque = deque()
jump_producer = threading.Thread(target=add_jumpers_to_deque, kwargs={'article_deque':article_deque})
detect_producer = threading.Thread(target=add_detected_to_deque, kwargs={'article_deque':article_deque})
consumer = threading.Thread(target=convert_and_upload, kwargs={'article_deque':article_deque})

print 'starting infinite loops now'
jump_producer.start()
detect_producer.start()
consumer.start()

jump_producer.join()
detect_producer.join()
consumer.join()
print 'finished' #this should never be reached if all loops are suffiicently infinite.
