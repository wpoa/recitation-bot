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
import status_page

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
    logging.info('reporting status with success %s' % str(success))
    status_page.make_status_page(doi=doi, success=success, 
                                 error_msg=status_msg,
                                 ja = ja, inqueue=False)

    #log all the failures
    if success:
        #twython_access.update_status(ja)
        logging.info('doi: %s, succeed' % doi)
    if not success:
        logging.info('DOI: %s \nFAIL MESSAGE:%s' % (doi, status_msg) )
        faillog.info('DOI: %s <br />\nFAIL MESSAGE:%s <br /><br />\n' % (doi, status_msg) )



def convert_and_upload(article_deque):

    def process_journal_article(prev_ja, curr_ja, im_uploads, shelf, doi):
        try:
            curr_ja.get_pmcid()
            curr_ja.get_targz()
            curr_ja.extract_targz()
            logging.info('ja phase: %s' % str(curr_ja.phase))
            curr_ja.find_nxml()
            curr_ja.extract_metadata()
            curr_ja.xslt_it()
            
            curr_ja.upload_images(im_uploads)
            #is this dangerous brain surgery? im not sure.
            if prev_ja: #that means we have a donor brain for surgery
                surgery_map = {'commons':'images',
                               'equations':'equations',
                               'tables':'tables'}
                #now we're putting in the things we didn't send to upload
                for sitestr, flag in im_uploads.iteritems():
                    if not flag:
                        curr_ja.metadata[surgery_map[sitestr]] = prev_ja.metadata[surgery_map[sitestr]]
            
            curr_ja.get_mwtext_element()
            curr_ja.replace_image_names_in_wikitext()
            curr_ja.replace_supplementary_material_links_in_wikitext()
            curr_ja.push_to_wikisource()
            curr_ja.push_redirect_wikisource()
            shelf[doi] = curr_ja
            shelf.sync()
            report_status(doi, curr_ja, None, success=True)
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
            logging.info(doi_article)
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
                im_uploads = {'commons':True, 'equations':True, 'tables':True}
                process_journal_article(prev_ja=prev_ja, curr_ja=curr_ja, im_uploads=im_uploads, shelf=shelf, doi=doi)           

#DOI was in shelf, but maybe we are repuploading
            else:
                logging.info('doi %s was in shelf' % doi)
                if not reupload:
                    logging.info('doi %s is being ignored because reupload was not on' % doi)
                else:
                    logging.info('doi %s is being processed because a reuploade parameter was found' % doi)
                    prev_ja = shelf[doi]
                    #Default to false
                    im_uploads = {'commons':False, 'equations':False, 'tables':False}
                    im_up_map = {'reupload_images':'commons',
                                 'reupload_equations':'equations',
                                 'reupload_tables':'tables'}
                    for reup in reupload:
                        if reup != 'reupload_text': #we always redo the text
                            im_uploads[im_up_map[reup]] = True
                    logging.info(str(im_uploads))
                    process_journal_article(prev_ja=prev_ja, curr_ja=curr_ja, im_uploads=im_uploads, shelf=shelf, doi=doi)
                    
        
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
