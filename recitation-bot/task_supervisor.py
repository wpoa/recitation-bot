from journal_article import journal_article
import os
import pywikibot
import shelve

if __name__ == '__main__':
    shelf = shelve.open('journal_shelf', writeback=False)
    
    static_vars = {"data_dir" : '/home/notconfusing/workspace/recitation-bot/data',
                       "jats2mw_xsl" : '/home/notconfusing/workspace/JATS-to-Mediawiki/jats-to-mediawiki.xsl',
                       "wikisource_site" : 'en',    
                       "wikisource_basepath" : 'Wikisource:WikiProject_Open_Access/Programmatic_import_from_PubMed_Central/',
                       "image_extensions": ['jpg', 'jpeg', 'png']}
    
    static_vars_test = {"data_dir" : '/home/notconfusing/workspace/recitation-bot/data',
                   "jats2mw_xsl" : '/home/notconfusing/workspace/JATS-to-Mediawiki/jats-to-mediawiki.xsl',
                   "wikisource_site" : 'en',    
                   "wikisource_basepath" : 'Wikisource:WikiProject_Open_Access/Programmatic_import_from_PubMed_Central/Test/',
                   "image_extensions": ['jpg', 'jpeg', 'png']}

    for doi in ['10.1155/S1110724304404033', '10.1186/1742-4690-2-11', '10.1186/1471-2156-10-59', '10.3897/zookeys.324.5827', '10.1371/journal.pone.0012292', '10.1186/1745-6150-1-19', '10.1371/journal.pbio.0020207', '10.1371/journal.pmed.0050045', '10.1371/journal.pgen.0020220', '10.1371/journal.pbio.1000436']:
        if doi not in shelf.keys():
            ja = journal_article(doi=doi, static_vars=static_vars_test)
            ja.get_pmcid()
            ja.get_targz()
            ja.extract_targz()
            ja.find_nxml()
            ja.xslt_it()
            ja.get_mwtext_element()
            ja.get_mwtitle_element()
            
            shelf[doi] = ja
            shelf.sync()
            #ja.push_to_wikisource()
            #ja.push_redirect_wikisource()
        else:
            ja = shelf[doi]
            if ja.phase['find_nxml']:
                ja.extract_metadata()
                ja.upload_images()
                ja.replace_image_names_in_wikitext()
                ja.push_to_wikisource()
            shelf[doi] = ja
    shelf.close()
