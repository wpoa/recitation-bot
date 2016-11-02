#!/usr/bin/env python

import logging, sys, os, time
from locate import locate
from contextlib import closing

# logging configuration

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

from logging.handlers import RotatingFileHandler
fh = RotatingFileHandler(filename = locate('recitation-bot.log'), maxBytes = 1000000, backupCount = 5, delay = True)
fh.setFormatter(formatter)
logger.addHandler(fh)

from multiprocessing import Pool, set_start_method

from journal_article import journal_article

def convert_and_upload(doi, shelf_filename):
    shelf = SQLiteShelf(shelf_filename)
    # parameters as key-value pairs, used like static variables
    # TODO probably get rid of this, make them actual parameters of the methods that use them
    parameters = {
        "data_dir" : locate('journal-download-data'),
        "jats2mw_xsl" : locate('JATS-to-Mediawiki/jats-to-mediawiki.xsl', project = True),
        "wikisource_site" : 'en',
        "wikisource_basepath" : 'Wikisource:WikiProject_Open_AccessProgrammatic_import_from_PubMed_Central/',
        "image_extensions": ['jpg', 'jpeg', 'png']
    }
    logger.debug("parameters are %s" % str(parameters))
    def process_journal_article(prev_ja, curr_ja, im_uploads):
        try:
            for (method, _) in curr_ja.__class__.phases:
                if method == 'get_mwtext_element':
                    #what's up with this hack? is this dangerous brain surgery? im not sure.
                    if prev_ja: #that means we have a donor brain for surgery
                        surgery_map = {'commons':'images',
                               'equations':'equations',
                               'tables':'tables'}
                        #now we're putting in the things we didn't send to upload
                        for sitestr, flag in im_uploads.iteritems():
                            if not flag:
                                curr_ja.metadata[surgery_map[sitestr]] = prev_ja.metadata[surgery_map[sitestr]]
                # refresh journal article's parameters to current ones (they should probably be passed in to the methods instead where needed)
                curr_ja.parameters = parameters
                method_params = {}
                getattr(curr_ja, method)(**method_params)
                logger.info('completed phase: %s' % method)
                shelf[doi] = curr_ja
                logger.debug("synced %s to shelf" % str(shelf[doi].doi))

        except Exception as e:
            logger.exception(e)
            logger.debug(e)

    reupload = ['reupload_images', 'reupload_equations', 'reupload_tables']
    curr_ja = journal_article(doi = doi, parameters = parameters)
    logger.info('working on doi %s and reupload was %s' % (str(doi), str(reupload)))

    try:
        prev_ja = shelf[doi]
    except KeyError: #DOI not in shelf
        logger.info('doi %s was not in shelf' % doi)
        prev_ja = None
        im_uploads = {'commons':True, 'equations':True, 'tables':True}

    else: #DOI was in shelf, but maybe we are re-uploading
        logger.info('doi %s was in shelf' % doi)
        if not reupload:
            logger.info('doi %s is being ignored because reupload was not on' % doi)
        else:
            logger.info('doi %s is being processed because a reupload parameter was found' % doi)
            #Default to false
            im_uploads = {'commons':False, 'equations':False, 'tables':False}
            im_up_map = {'reupload_images':'commons',
                         'reupload_equations':'equations',
                         'reupload_tables':'tables'}
            for reup in reupload:
                if reup != 'reupload_text': #we always redo the text
                    im_uploads[im_up_map[reup]] = True
            logger.info(str(im_uploads))
    process_journal_article(prev_ja=prev_ja, curr_ja=curr_ja, im_uploads=im_uploads)
    return doi

from sqliteshelf import SQLiteShelf
shelf_filename = locate('journal_shelf')

def submit_article(doi, pool):
	callback = lambda doi: logger.info('successfully completed %s' % str(doi))
	error_callback = lambda error: logger.info('error in job %s' % str(error))
	pool.apply_async( convert_and_upload, (doi, shelf_filename), callback = callback, error_callback = error_callback)

from sqlitequeue import SQLiteQueue
def run():
	with closing(SQLiteQueue(locate('work-fifo'))) as work_fifo:
		def poll_queue():
			while True:
				item = work_fifo.pop()
				if item: yield item
				else: time.sleep(1)
		with Pool(processes = 8, maxtasksperchild = 1) as pool:
			for doi in poll_queue():
				logger.debug("polled doi %s from queue" % str(doi))
				submit_article(doi, pool)

if __name__ == '__main__':
	run()

