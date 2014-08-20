# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import wget
import urllib
import tarfile
import os
from subprocess import call
import xml.etree.ElementTree as etree
import pywikibot
from collections import defaultdict
from functools import wraps
import re
import ast
import pmc_extractor
import commons_template
import helpers
import logging

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)

class journal_article():

    '''
    This class represents a journal article
    (the primary object for this application),
    and its lifecycle to make it to Wikisource.
    '''

    def __init__(self, doi, article, parameters):
        '''
        journal_articles are represented by dois
        '''
        if doi.startswith('http://dx.doi.org/'): # NOTE: https does not resolve
            doi_parts = doi.split('http://dx.doi.org/')
            doi = doi_parts[1] 
        self.doi = doi
        self.article = article
        self.parameters = parameters

        # Phases, for example: (a) downloaded article, (b) extracted article's
        # pmcid, (c) uploaded the images to commons, etc.
        self.phase = defaultdict(bool)

    # @TODO consider deprecating this for extract_metadata()
    # Already using OAMI method of getting PMID and PMCID
    def get_pmcid(self):
        idpayload = {'ids' : self.doi, 'format': 'json'}
        idconverter = requests.get('http://www.pubmedcentral.nih.gov/utils/idconv/v1.0/', params=idpayload)
        records = idconverter.json()['records']
        if len(records) == 1:
            # since we are supplying a single doi, assumes we receive only 1 record
            record = records[0]
        else:
            raise ConversionError(message='not just one pmcid for a doi',doi=self.doi)
        self.pmcid = record['pmcid']

        self.phase['get_pmcid'] = True

    # @TODO consider including .zip download as well or alternative
    def get_targz(self):
        # make request for archive file location
        archivefile_payload = {'id' : self.pmcid}
        archivefile_locator = requests.get('http://www.pubmedcentral.nih.gov/utils/oa/oa.fcgi', params=archivefile_payload)
        record = BeautifulSoup(archivefile_locator.content)
        # parse response for archive file location
        archivefile_url = record.oa.records.record.find(format='tgz')['href']
        archivefile_name = wget.filename_from_url(archivefile_url)
        complete_path_targz = os.path.join(self.parameters["data_dir"], archivefile_name)

        # @TODO For some reason, wget hangs and doesn't finish
        # archivefile = wget.download(archivefileurl, wget.bar_thermometer)
        # Using urllib.urlretrieve() instead of wget for now:

        # Download targz
        urllib.urlretrieve(archivefile_url, complete_path_targz)
        self.complete_path_targz = complete_path_targz

        self.phase['get_targz'] = True


    def extract_targz(self):
        try:
            directory_name, file_extension = self.complete_path_targz.split('.tar.gz')
            self.article_dir = directory_name
            tar = tarfile.open(self.complete_path_targz, 'r:gz')
            tar.extractall(self.parameters["data_dir"])

            self.phase['extract_targz'] = True

        except:
            raise ConversionError(message='trouble extracting the targz', doi=self.doi)

    def find_nxml(self):
        try:
            self.qualified_article_dir = os.path.join(self.parameters["data_dir"], self.article_dir)
            nxml_files = [file for file in os.listdir(self.qualified_article_dir) if file.endswith(".nxml")]
            if len(nxml_files) != 1:
                raise ConversionError(message='we need exactly 1 nxml file, no more, no less', doi=self.doi)
            nxml_file = nxml_files[0]
            self.nxml_path = os.path.join(self.qualified_article_dir, nxml_file)

            self.phase['find_nxml'] = True

        except ConversionError as ce:
            raise ce
        except:
            raise ConversionError(message='could not traverse the search directory for nxml files', doi=self.doi)

    def extract_metadata(self):
        self.metadata = pmc_extractor.extract_metadata(self.nxml_path)
        if not any([self.metadata['article-license-url'],
                   self.metadata['article-license-text'],
                   self.metadata['article-copyright-statement']]):
            raise ConversionError(message='no article license', doi=self.doi)

        self.phase['extract_metadata'] = True

    def xslt_it(self):
        # Try to apply XSL transform from XML to MediaWiki markup (wikitext)
        try:
            doi_file_name = self.doi + '.mw.xml'
            mw_xml_file = os.path.join(self.parameters["data_dir"], doi_file_name)
            doi_file_name_pre_slash = doi_file_name.split('/')[0]
            if doi_file_name_pre_slash == doi_file_name:
                raise ConversionError(message='I think there should be a slash in the doi', doi=self.doi)
            mw_xml_dir = os.path.join(self.parameters["data_dir"], doi_file_name_pre_slash)
            if not os.path.exists(mw_xml_dir):
                os.makedirs(mw_xml_dir)
            mw_xml_file_handle = open(mw_xml_file, 'w')
            # @TODO may use python lxml library instead of shell call to `xsltproc`
            # http://lxml.de/xpathxslt.html#xslt
            # Unclear if there will be a difference in performance / accuracy
            call_return = call(['xsltproc', self.parameters["jats2mw_xsl"], self.nxml_path], stdout=mw_xml_file_handle)
            if call_return == 0: #things went well
                mw_xml_file_handle.close()
                self.mw_xml_file = mw_xml_file

                self.phase['xslt_it'] = True

            else:
                raise ConversionError(message='something went wrong during the xsltprocessing', doi=self.doi)
        except:
            raise ConversionError(message='something went wrong, probably munging the file structure', doi=self.doi)

    # @TODO consider replacing etree with beautifulsoup (bs4), since we already
    # use bs4 above, should not be additional memory cost to traverse it again.
    # Alternatively, could replace bs4 with etree for performance.
    def get_mwtext_element(self):
        try:
            tree = etree.parse(self.mw_xml_file)
            root = tree.getroot()
            mwtext = root.find('mw:page/mw:revision/mw:text', namespaces={'mw':'http://www.mediawiki.org/xml/export-0.8/'})
            self.wikitext = mwtext.text

            self.phase['get_mwtext_element'] = True

        except:
            raise ConversionError(message='no text element')


    def upload_images(self):

        def find_right_extension(image):
            '''this is a helper to get determine what extension to use'''
            for extension in ['.jpg','.png','.jpeg','.JPEG', '.PNG', '.tif', '.tiff', '.TIF', '.TIFF', '.svg', '.SVG']:
                image_file = image + extension
                qualified_image_location = os.path.join(self.qualified_article_dir, image_file)
                if os.path.isfile(qualified_image_location):
                    return image_file, qualified_image_location
        #this means no valid extension was found and returned
                raise ConversionError(message='%s is not a jpg or png uploadable' % qualified_image_location, doi=self.doi)

        commons = pywikibot.Site('commons', 'commons')
        if not commons.logged_in():
            commons.login()

        for image in self.metadata['images'].iterkeys():

            image_file, qualified_image_location = find_right_extension(image)
            
            harmonized_name = helpers.harmonizing_name(image_file, self.metadata['article-title'])
            #print harmonized_name
            image_page = pywikibot.ImagePage(commons, harmonized_name)
            page_text = commons_template.page(self.metadata, self.metadata['images'][image]['caption'])
            image_page._text = page_text
            try:
                commons.upload(imagepage=image_page, source_filename=qualified_image_location, 
                               comment='Automatic upload of media from: [[doi:' + self.doi+']]',
                               ignore_warnings=False)
                               # "ignore_warnings" means "overwrite" if True
                logging.info('Uploaded image %s' % image_file)
                self.metadata['images'][image]['uploaded_name'] = harmonized_name
            except pywikibot.exceptions.UploadWarning as warning:
                warning_string = unicode(warning)
                if warning_string.startswith('Uploaded file is a duplicate of '):
                    liststring = warning_string.split('Uploaded file is a duplicate of ')[1][:-1]
                    duplicate_list = ast.literal_eval(liststring)
                    duplicate_name = duplicate_list[0]
                    print 'duplicate found: ', duplicate_name
                    logging.info('Duplicate image %s' % image_file)
                    self.metadata['images'][image]['uploaded_name'] = duplicate_name
                elif warning_string.endswith('already exists.'):
                    logging.info('Already exists image %s' % image_file)
                    self.metadata['images'][image]['uploaded_name'] = harmonized_name
                    #TODO check to see if there is any difference
                    existing_page_text = image_page.get()
                    if existing_page_text != page_text:
                        image_page.put(newtext=page_text, comment='Updating description')
                else:
                    raise

        self.phase['upload_images'] = True

    def replace_image_names_in_wikitext(self):
        replacing_text = self.wikitext
        for image in self.metadata['images'].iterkeys():
            extensionless_re = r'File:(' + image + r')\|'
            new_file_text = r'File:' + self.metadata['images'][image]['uploaded_name'] + r'|'
            replacing_text, occurences = re.subn(extensionless_re, new_file_text, replacing_text)
            if occurences != 1:
                print occurences, image
        # print replacing_text
        self.image_fixed_wikitext = replacing_text

        self.phase['replace_image_names_in_wikitext'] = True

    def push_to_wikisource(self):
        site = pywikibot.Site(self.parameters["wikisource_site"], "wikisource")
        self.wikisource_title = self.parameters["wikisource_basepath"] + helpers.title_cleaner(self.metadata['article-title'])
        if len(self.wikisource_title) > 220:
                self.wikisource_title = self.wikisource_title[:220]
        page = pywikibot.Page(site, self.wikisource_title)
        comment = "Imported [[doi:"+self.doi+"]] from http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id="+self.pmcid+" by recitation-bot v0.1"
        page.put(newtext=self.image_fixed_wikitext, botflag=True, comment=comment)
        self.wiki_link = page.title(asLink=True)

        self.phase['push_to_wikisource'] = True

    def push_redirect_wikisource(self):
        site = pywikibot.Site(self.parameters["wikisource_site"], "wikisource")
        page = pywikibot.Page(site, self.parameters["wikisource_basepath"] + self.doi)
        comment = "Making a redirect"
        redirtext = '#REDIRECT [[' + self.wikisource_title +']]'
        page.put(newtext=redirtext, botflag=True, comment=comment)

        self.phase['push_redirect_wikisource'] = True

    # Returns HTML string for link to uploaded WikiSource article
    def htmlstr(self):
        return_string = 'See <a href="https://en.wikisource.org/wiki/%s">%s</a>\n' % (self.wikisource_title, self.wikisource_title)
        for metadata, val in self.metadata.iteritems():
            return_string += u'<p>' + unicode(metadata) + u':' + unicode(val) + u'</p>' + u'\n'
        return return_string

class ConversionError(Exception):
    def __init__(self, message, doi):
        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        # Store DOI as error in object
        # @TODO do something with error_doi?
        self.error_doi = doi
