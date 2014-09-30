# -*- coding: utf-8 -*-

from journal_article import journal_article
import twython_access
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
import ast

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
                doi, reupload_list_str = doi_input.split('\t')
                reupload = ast.literal_eval(reupload_list_str) 
                article_deque.append({'doi':doi,'reupload':reupload,'article':None})
        time.sleep(10)

def add_detected_to_deque(article_deque):
    logging.debug('detector thread launched')
    finder = doi_finder(lang='test2wiki')
    finder.find_new_doi_article_pairs(article_deque)

def report_status(doi, ja, status_msg, success):
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
</html>''' % (doi, success_str, status_msg)
    waiting_page.write(waiting_text.encode('utf-8'))
    waiting_page.close()

    #log off all the failures
    if success:
        twython_access.update_status(ja)
    if not success:
        logging.info('DOI: %s \nFAIL MESSAGE:%s' % (doi, status_msg) )
        faillog.info('DOI: %s <br />\nFAIL MESSAGE:%s <br /><br />\n' % (doi, status_msg) )



def convert_and_upload(article_deque):

    def process_journal_article(prev_ja, curr_ja, text_only, shelf, doi):
        try:
            curr_ja.get_pmcid()
            curr_ja.get_targz()
            curr_ja.extract_targz()
            curr_ja.find_nxml()
            curr_ja.extract_metadata()
            curr_ja.xslt_it()
            
            logging.info('text_only?'+str(text_only))
            if not text_only:
                curr_ja.upload_images()
            else:
                #is this dangerous brain surgery? im not sure.
                curr_ja.metadata['images'] = prev_ja.metadata['images']
            
            curr_ja.get_mwtext_element()
            curr_ja.replace_image_names_in_wikitext()
            curr_ja.replace_supplementary_material_links_in_wikitext()
            curr_ja.push_to_wikisource()
            curr_ja.push_redirect_wikisource()
            shelf[doi] = curr_ja
            shelf.sync()
            report_status(doi, curr_ja, curr_ja.htmlstr(), success=True)
        except Exception as e:
            logging.exception(e)
            logging.debug(e)
            report_status(doi, curr_ja, str(e), success=False)

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
            article = doi_article['article']
            curr_ja = journal_article(doi=doi, article=article, parameters=parameters)
            logging.debug('associated article %s' % article)
            logging.info('working on doi %s and reupload was %s' % (str(doi), str(reupload)))
            #DOI not in shelf
            if doi not in shelf.keys():
                logging.info('doi %s was not in shelf' % doi)
                prev_ja = None
                process_journal_article(prev_ja=prev_ja, curr_ja=curr_ja, text_only=False, shelf=shelf, doi=doi)           

#DOI was in shelf, but maybe we are repuploading
            else:
                logging.info('doi %s was in shelf' % doi)
                if not reupload:
                    logging.info('doi %s is being ignored because reupload was not on' % doi)
                else:
                    prev_ja = shelf[doi]
                    if 'reupload_images' in reupload:
                        text_only = False
                    else: #this condition should mean that reupload is ['reupload_text']
                        text_only = True
                    process_journal_article(prev_ja=prev_ja, curr_ja=curr_ja, text_only=text_only, shelf=shelf, doi=doi)
                    
        
        except IndexError: #nothing in the deque
            logging.info('nothing in deque sleepytime')
            time.sleep(10)
            continue
    shelf.close()



#The main threads
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
