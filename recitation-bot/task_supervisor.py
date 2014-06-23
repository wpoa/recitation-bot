# -*- coding: utf-8 -*-

from journal_article import journal_article
import os
import pywikibot
import shelve

if __name__ == '__main__':
    '''For every DOI-article pair in existence it can be one of the following statuses to us:
    1. previously_done #we've already processed it
    2. in_progress #it's in our queue to do
    3. not_doing #we've manually specified not to do this pair
    4. new_additions #they doi is on use in wikipedia and we have to detect it. 
    '''

    # creates shelf store for article data (history)
    shelf = shelve.open('journal_shelf', writeback=False)

    # parameters as key-value pairs, used like static variables
    parameters = {
        "data_dir" : '/home/notconfusing/workspace/recitation-bot/data',
        "jats2mw_xsl" : '/home/notconfusing/workspace/JATS-to-Mediawiki/jats-to-mediawiki.xsl',
        "wikisource_site" : 'en',
        "wikisource_basepath" : 'Wikisource:WikiProject_Open_Access/Programmatic_import_from_PubMed_Central/',
        "image_extensions": ['jpg', 'jpeg', 'png']
    }

    # parameters used for test endpoints
    test_parameters = {
        "data_dir" : '/home/notconfusing/workspace/recitation-bot/data',
        "jats2mw_xsl" : '/home/notconfusing/workspace/JATS-to-Mediawiki/jats-to-mediawiki.xsl',
        "wikisource_site" : 'en',
        "wikisource_basepath" : 'Wikisource:WikiProject_Open_Access/Programmatic_import_from_PubMed_Central/Test/',
        "image_extensions": ['jpg', 'jpeg', 'png']
    }

    # list of dois to store
    #dois = ['10.1155/S1110724304404033', '10.1186/1742-4690-2-11', '10.1186/1471-2156-10-59', '10.3897/zookeys.324.5827', '10.1371/journal.pone.0012292', '10.1186/1745-6150-1-19', '10.1371/journal.pbio.0020207', '10.1371/journal.pmed.0050045', '10.1371/journal.pgen.0020220', '10.1371/journal.pbio.1000436']
    dois =[u'10.3897/BDJ.2.e1019', u'10.1186/1471-2148-9-210', u'10.3897/zookeys.364.6109', u'10.3897/zookeys.333.5795']
    # main loop
    # take dois, instantiate article object
    # under certain conditions, shelf the object, push to wikisource
    for doi in dois:
        if doi not in shelf.keys():
            print doi
            ja = journal_article(doi=doi, parameters=test_parameters)
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
    shelf.close()
