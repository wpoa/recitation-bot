#!/usr/bin/env python

import logging, sys

from locate import locate

from flask import Flask, request, jsonify, render_template, url_for

from sqlitequeue import SQLiteQueue

# initialize app
app = Flask(__name__)

work_fifo = SQLiteQueue(locate('work-fifo'))

def submit_article(doi):
	work_fifo.push(doi)

from sqliteshelf import SQLiteShelf
shelf_filename = locate('journal_shelf')
shelf_global = SQLiteShelf(shelf_filename)

app_base = '/recitation-bot/'
@app.route('/', methods = ['GET', 'POST'])
@app.route(app_base, methods = ['GET', 'POST'])
def index():
    m = ""

    if 'DOI-query' in request.form:
        doi = request.form['DOI-query']
        try:
            doistatus = shelf_global[doi]
            m += "Info for %s:" % doi
            return render_template('index', message = m, doi_info = doistatus.phase.items(), app_base = app_base)
        except KeyError:
            m += "DOI %s not found." % doi
            return render_template('index', message = m, app_base = app_base)

    if 'DOI-submission' in request.form:
        doi = request.form['DOI-submission']
        submit_article(doi)
        if doi not in work_fifo.items():
            m += "%s not found in work_fifo"
        else:
            m += "Added %s to queue for processing." % doi
        return render_template('index', message = m, app_base = app_base)

    if 'DOI-list' in request.form:
        m += 'DOIs:<br/>'
        for key in shelf_global.keys():
            m += str(key)+"<br/>\n"
        return render_template('index', message = m, app_base = app_base)

    if 'show-work-queue' in request.form:
        m += "Work queue:<br/>"
        for item in work_fifo.items():
            m += str(item)+"<br/>\n"
        return render_template('index', message = m, app_base = app_base)

    else:
        m += "No action requested. Enter request below."
        return render_template('index', message = m, app_base = app_base)

#app.debug = True # This does not work right with multiprocessing

from multiprocessing import Process
from importlib import import_module
background_process_module = import_module('background-process')
background_process = Process(target = background_process_module.run)

background_process.start()

def shutdown():
	background_process.join()

from atexit import register
register(shutdown)

if __name__ == '__main__':
	try:
		if len(sys.argv) > 1:
			port = int(sys.argv[1])
		else:
			port = 8080
			app.run(port = port)
	finally:
		shutdown()

