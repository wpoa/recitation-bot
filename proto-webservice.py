#!/usr/bin/env python

import logging, sys

from multiprocessing import Process, Lock, Queue
from flask import Flask, request, jsonify, render_template, url_for

import os

labs_home = '/data/project/recitation-bot/'
if os.path.exists(labs_home):
	running_on_labs = True
	os.chdir(os.path.join(labs_home, 'new-bot'))
else:
	running_on_labs = False

def locate(path):
	return os.path.join(labs_home if running_on_labs else '.', path)

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

# initialize app
app = Flask(__name__)

from journal_article import journal_article

def convert_and_upload(doi, shelf):
    # parameters as key-value pairs, used like static variables
    # TODO probably get rid of this, make them actual parameters of the methods that use them
    parameters = {
        "data_dir" : locate('journal-download-data'),
        "jats2mw_xsl" : locate('JATS-to-Mediawiki/jats-to-mediawiki.xsl'),
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
        process_journal_article(prev_ja=prev_ja, curr_ja=curr_ja, im_uploads=im_uploads)

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

def open_shelf(shelf_filename):
    import shelve
    # we'll let the lock import come from the context so we get the right kind

    from contextlib import closing

    class ConcurrentShelf:
        def __init__(self, filename):
            self.lock = Lock()
            self.filename = filename

        def get(self, key):
            r = None
            with self.lock:
                with closing(shelve.open(self.filename)) as shelf:
                    r = shelf[key]
                    shelf.sync() # redundant with with statement? eh
            return r

        def set(self, key, value):
            with self.lock:
                with closing(shelve.open(self.filename)) as shelf:
                    shelf[key] = value
                    shelf.sync() # redundant with with statement? eh

        def __getitem__(self, key):
            return self.get(key)

        def __setitem__(self, key, value):
            self.set(key, value)

    return ConcurrentShelf(shelf_filename)

action_queue = Queue()

def poll_queue(shelf):
	from time import sleep
	while True:
		try:
			action = action_queue.get()
			if action == set('terminate'): # wrap in a set so can't be passed in via form
				sys.exit(0)
			else:
				doi = action
				logger.info("Uploading %s." % doi)
				convert_and_upload(doi, shelf)
		except IndexError:
			sleep(1)

shelf_filename = locate('journal_shelf')
shelf_global = open_shelf(shelf_filename)

app_base = '/recitation-bot/'
@app.route('/', methods = ['GET', 'POST'])
@app.route(app_base, methods = ['GET', 'POST'])
def index():
    if 'DOI-query' in request.form:
        doi = request.form['DOI-query']
        try:
            doistatus = shelf_global[doi]
            m = "Info for %s: %s" % (doi, str(doistatus.phase))
            return render_template('index', message = m, doi_info = doistatus.items(), app_base = app_base)
        except KeyError:
            m = "DOI %s not found." % doi
            return render_template('index', message = m, app_base = app_base)
    if 'DOI-submission' in request.form:
        doi = request.form['DOI-submission']
        action_queue.put(doi)
        m = "Added %s to queue for processing." % doi
        return render_template('index', message = m, app_base = app_base)
    else:
        m = "No DOI requested. Enter request below."
        return render_template('index', message = m, app_base = app_base)

#app.debug = True # This does not work right with multiprocessing

# These two are used for managing global state
# http://flask.pocoo.org/docs/0.11/appcontext/
from flask import g

def get_worker(name):
    full_name = '_worker_' + name
    with app.app_context():
    # within this block, current_app points to app.
        worker = getattr(g, full_name, None)
        if worker is None:
            setattr(g, full_name, Process(target = poll_queue, args = (shelf_global,)))
            worker = getattr(g, full_name, None)
            worker.start()
        return worker

background_process = get_worker('doi_queue')

@app.teardown_appcontext
def teardown_workers(exception):
	action_queue.put(set('terminate'))
	background_process.join()

if __name__ == '__main__':
	try:
		if len(sys.argv) > 1:
			port = int(sys.argv[1])
		else:
			port = 8080
			app.run(port = port)
	finally:
		teardown_background(None)

