# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import wget
import urllib.request, urllib.parse, urllib.error
import tarfile
import os
from subprocess import call
import xml.etree.ElementTree as etree
from functools import wraps
import re
import ast
import pmc_extractor
import commons_template
import helpers
import logging
import time
import mwclient
from datetime import datetime
from locate import locate

wiki_uname, wiki_passwd = eval( open( locate('.pywikibot/secretsfile') ).read() )

from collections import OrderedDict

logger = logging.getLogger()

class journal_article():

    '''
    This class represents a journal article
    (the primary object for this application),
    and its lifecycle to make it to Wikisource.
    '''
    phases = [
        ('get_pmcid', None),
        ('get_targz', None),
        ('extract_targz', None),
        ('find_nxml', None),
        ('extract_metadata', None),
        ('xslt_it', None),
        ('get_mwtext_element', None),
        ('upload_images', None),
        ('replace_image_names_in_wikitext', None),
        ('replace_supplementary_material_links_in_wikitext', None),
        ('push_to_wikisource', None),
        ('push_redirect_wikisource', None)
    ]

    def __init__(self, doi, parameters):
        '''
        journal_articles are represented by dois
        '''
        if doi.startswith('http://dx.doi.org/'): # NOTE: https does not resolve
            doi_parts = doi.split('http://dx.doi.org/')
            doi = doi_parts[1]
        self.doi = doi
        self.parameters = parameters

        #use these for image uploading
        self.commons = ('commons', 'commons', 'images')
        self.equations = (self.parameters['wikisource_site'], 'wikisource', 'equations')
        self.tables = (self.parameters['wikisource_site'], 'wikisource', 'tables')

        # Phases, for example: (a) downloaded article, (b) extracted article's
        # pmcid, (c) uploaded the images to commons, etc.
        self.init_phases()

    def init_phases(self):
        self.phase = OrderedDict(self.__class__.phases)

    def refresh(self):
        '''
        This method does what is necessary to update an old journal_article object loaded from the shelf
        currently it just makes self.phase an OrderedDict if it is not already
        '''
        if type(self.phase) is not OrderedDict:
            self.init_phases()

    # @TODO consider deprecating this for extract_metadata()
    # Already using OAMI method of getting PMID and PMCID
    def get_pmcid(self):
        idpayload = {'ids' : self.doi, 'format': 'json'}
        reachable = False
        for retries in range(5):
            try:
                idconverter = requests.get('http://www.pubmedcentral.nih.gov/utils/idconv/v1.0/', params=idpayload)
                try:#if the doi wasnt in pmc you can't get the records out, if the api returned not-json the you get a value error
                    records = idconverter.json()['records']
                except KeyError:
                    raise ConversionError(message='probably the doi has a typo or extra text at the front or back', doi=self.doi)

                if len(records) == 1:
                    # since we are supplying a single doi, assumes we receive only 1 record
                    record = records[0]
                    if 'status' in record and record['status'] == 'error':
                        # a PMCID was not found for this
                        reachable = True
                        self.pmcid = None
                        break
                    else:
                        self.pmcid = record['pmcid']
                else:
                    raise ConversionError(message='not just one pmcid for a doi',doi=self.doi)

                reachable = True
                break
            except ValueError as e:
                pass
        if not reachable:
            raise ConversionError(message='usually this is because PMCs API has gone down. Try clicking this URL to see: <br /> <a href="http://www.pubmedcentral.nih.gov/utils/idconv/v1.0/?ids=%s&format=json">API link</a>' % self.doi  ,doi=self.doi)

        self.phase['get_pmcid'] = datetime.now()

    # @TODO consider including .zip download as well or alternative
    def get_targz(self):
        # make request for archive file location
        archivefile_payload = {'id' : self.pmcid}
        archivefile_locator = requests.get('http://www.pubmedcentral.nih.gov/utils/oa/oa.fcgi', params=archivefile_payload)
        record = BeautifulSoup(archivefile_locator.content, 'lxml')
        # parse response for archive file location
        archivefile_url = record.oa.records.record.find(format='tgz')['href']
        archivefile_name = wget.filename_from_url(archivefile_url)
        complete_path_targz = os.path.join(self.parameters["data_dir"], archivefile_name)

        # @TODO For some reason, wget hangs and doesn't finish
        # archivefile = wget.download(archivefileurl, wget.bar_thermometer)
        # Using urllib.urlretrieve() instead of wget for now:

        # Download targz
        urllib.request.urlretrieve(archivefile_url, complete_path_targz)
        self.complete_path_targz = complete_path_targz

        self.phase['get_targz'] = datetime.now()


    def extract_targz(self):
        try:
            directory_name, file_extension = self.complete_path_targz.split('.tar.gz')
            self.article_dir = directory_name
            tar = tarfile.open(self.complete_path_targz, 'r:gz')
            tar.extractall(self.parameters["data_dir"])

            self.phase['extract_targz'] = datetime.now()

        except:
            raise ConversionError(message='trouble extracting the targz', doi=self.doi)

    def find_nxml(self):
        try:
            self.qualified_article_dir = self.article_dir
            nxml_files = [file for file in os.listdir(self.qualified_article_dir) if file.endswith(".nxml")]
            if len(nxml_files) != 1:
                raise ConversionError(message='we need exactly 1 nxml file, no more, no less', doi=self.doi)
            nxml_file = nxml_files[0]
            logger.info('the nxml file being used is: %s' % str(nxml_file))
            self.nxml_path = os.path.join(self.qualified_article_dir, nxml_file)

            self.phase['find_nxml'] = datetime.now()

        except ConversionError as ce:
            raise ce
        except:
            raise ConversionError(message='could not traverse the search directory for nxml files', doi=self.doi)

    def extract_metadata(self):
        self.metadata = pmc_extractor.extract_metadata(self.nxml_path)
        logger.info(str(self.metadata))
        if not any([self.metadata['article-license-url'],
                   self.metadata['article-license-text'],
                   self.metadata['article-copyright-statement']]):
            raise ConversionError(message='no article license', doi=self.doi)

        self.phase['extract_metadata'] = datetime.now()

    def xslt_it(self):
        from lxml import etree
        doi_file_name = self.doi + '.mw.xml'
        mw_xml_file_name = os.path.join(self.parameters["data_dir"], doi_file_name)
        doi_file_name_pre_slash = doi_file_name.split('/')[0]
        if doi_file_name_pre_slash == doi_file_name:
            raise ConversionError(message='I think there should be a slash in the doi', doi=self.doi)
        mw_xml_dir = os.path.join(self.parameters["data_dir"], doi_file_name_pre_slash)
        if not os.path.exists(mw_xml_dir):
            os.makedirs(mw_xml_dir)
        new_mw_xml_file = open(mw_xml_file_name, 'w', encoding = 'utf-8')
        xslt_root = etree.parse(open(self.parameters["jats2mw_xsl"], 'r', encoding = 'utf-8'))
        transform = etree.XSLT(xslt_root)
        old_mw_xml_root = etree.parse(open(self.nxml_path, 'r'))
        result = transform(old_mw_xml_root)
        new_mw_xml_file.write(str(result))
        new_mw_xml_file.close()
        self.mw_xml_file = mw_xml_file_name

        self.phase['xslt_it'] = datetime.now()

    # @TODO consider replacing etree with beautifulsoup (bs4), since we already
    # use bs4 above, should not be additional memory cost to traverse it again.
    # Alternatively, could keep bs4 over etree for performance.
    def get_mwtext_element(self):
        try:
            tree = etree.parse(open(self.mw_xml_file, 'r', encoding = 'utf-8'))
            root = tree.getroot()
            mwtext = root.find('page/revision/text', namespaces={'mediawiki':'http://www.mediawiki.org/xml/export-0.8/'})
            logger.debug('tree is ' + str(tree) + ' mwtext is ' + str(mwtext))
            self.wikitext = mwtext.text

            self.phase['get_mwtext_element'] = datetime.now()

        except:
            raise ConversionError(message='no text element')

    def upload_images(self, im_uploads):
        #this is the upload procedure which we call in a second
        def upload(site, metadata, image_dict):
            for image in metadata[image_dict]:
                image_file, qualified_image_location = helpers.find_right_extension(image, self.qualified_article_dir)

                logger.info(image_file)

                if image_file: #we found a valid image file
                    harmonized_name = helpers.harmonizing_name(image_file, metadata['article-title'])
                    image_page = mwclient.page.Page(site, harmonized_name)
                    page_text = commons_template.page(metadata, metadata[image_dict][image]['caption'])
                    image_page._text = page_text
                    try:
                        site.upload(open(qualified_image_location, 'rb'),
                                    harmonized_name,
                                    'Automatic upload of media from: [[doi:' + self.doi+']]',
                                   )
                        logger.info('Uploaded image %s' % image_file)
                        metadata[image_dict][image]['uploaded_name'] = harmonized_name
                        image_page.save(text = page_text, bot = True)
                    except e:
                        logger.info('Error uploading image %s' % image_file)

        #now we start calling the uploader
        upload_sites = list()
        sites_map = {'commons':'commons.wikimedia.org',
                     'equations':'en.wikisource.org',
                     'tables':'en.wikisource.org'}
        for sitestr, flag in im_uploads.items():
            upload_sites.append(sites_map[sitestr])

        for lang, family, image_dict in upload_sites:
            site = mwclient.Site(lang, family)
            site.login(wiki_uname, wiki_passwd)

            upload(site, self.metadata, image_dict)

        self.phase['upload_images'] = datetime.now()

    def replace_image_names_in_wikitext(self):

        def replace(metadata, image_dict, replacing_text):
            for image in metadata[image_dict].keys():
                extensionless_re = r'File:(' + image + r')\|'
                logger.info('extensionless re: %s' % extensionless_re)
                try:
                    new_file_text = r'File:' + metadata[image_dict][image]['uploaded_name'] + r'|'
                    replacing_text, occurrences = re.subn(extensionless_re, new_file_text, replacing_text)
                    logger.info('re stuff: %s, %s, %s' % (extensionless_re, new_file_text,  occurrences) )
                    if occurrences != 1:
                        logger.info('not one replace occurence %s, %s ' % (occurrences, image))
                except KeyError:
                    #the file may not have been uploaded and thus not have an uploaded name
                    continue #on to the next image
            return replacing_text


        self.image_fixed_wikitext = self.wikitext #it will become image_fixed_wikitext
        for lang, family, image_dict in [self.commons, self.equations, self.tables]:
            #we don't need lang or family for this, but i keep the loop just for formalism
            logger.info('now replacing: %s' % image_dict)
            self.image_fixed_wikitext = replace(self.metadata, image_dict, self.image_fixed_wikitext)

        self.phase['replace_image_names_in_wikitext'] = datetime.now()

    def replace_supplementary_material_links_in_wikitext(self):
        replacing_text = self.image_fixed_wikitext
        for material in self.metadata['supplementary-materials']:
            extensionless_re = r'\[\[File:(' + material['href'] + r').*?\]\]'
            try:
                # Check if this is an OAMI-uploaded file on commons, or not
                href_no_extension = os.path.splitext(material['href'])[0]
                found_file = helpers.find_file_in_commons(href_no_extension)
                if found_file:
                    # Use commons file instead of external URL
                    new_file_text = r'[[' + found_file + r']]'
                else:
                    # Use external URL to PMC file
                    new_file_text = r'[' + material['url'] + r' ' + material['href']  + r']'

                replacing_text, occurrences = re.subn(extensionless_re, new_file_text, replacing_text)
                if occurrences != 1:
                    print(occurrences, material)
                    # print replacing_text
            except KeyError:
                continue #on to the next image
        # replace the text
        self.image_fixed_wikitext = replacing_text

        self.phase['replace_supplementary_material_links_in_wikitext'] = datetime.now()

    def push_to_wikisource(self):
        logger.info('connecting to wikisource')
        site = mwclient.Site('en.wikisource.org')
        site.login(wiki_uname, wiki_passwd)
        logger.info('made Site object %s' % str(site))
        self.wikisource_title = self.parameters["wikisource_basepath"] + helpers.title_cleaner(self.metadata['article-title'])
        self.wikisource_title = self.wikisource_title[:255]
        page = mwclient.page.Page(site, self.wikisource_title)
        logger.info('made Page object %s' % str(page))
        comment = "Imported [[doi:"+self.doi+"]] from http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id="+self.pmcid+" by recitation-bot v0.1"
        logger.info('about to push doi %s with page %s to wikisource' % (str(self.doi), str(page)))
        page.save(bot = True, text = self.image_fixed_wikitext)
        logger.info('pushed '+self.doi+' to wikisource')
        # self.wiki_link = page.title(asLink=True) # TODO currently broken, need to reimplement since unsupported by mwclient

        self.phase['push_to_wikisource'] = datetime.now()

    def push_redirect_wikisource(self):
        site = mwclient.Site('en.wikisource.org')
        site.login(wiki_uname, wiki_passwd)
        page = mwclient.page.Page(site, self.parameters["wikisource_basepath"] + self.doi)
        comment = "Making a redirect"
        redirtext = '#REDIRECT [[' + self.wikisource_title +']]'
        page.text(redirtext)
        page.save(text = redirtext, bot = True)

        self.phase['push_redirect_wikisource'] = datetime.now()


    def urlstr(self):
        https = "https://en.wikisource.org/wiki/%s" % self.wikisource_title
        safe = https.replace(' ','_')
        return safe
    # Returns HTML string for link to uploaded WikiSource article

    def doiurl(self):
        lang = self.parameters["wikisource_site"]
        base = self.parameters["wikisource_basepath"]
        doi_end = self.doi
        https = "https://%s.wikisource.org/wiki/%s%s" % (lang, base, doi_end)
        return https

    def htmlstr(self):
        return_string = 'See <a href="https://en.wikisource.org/wiki/%s">%s</a>\n' % (self.wikisource_title, self.wikisource_title)
        for metadata, val in self.metadata.items():
            return_string += '<p>' + str(metadata) + ':' + str(val) + '</p>' + '\n'
        return return_string

class ConversionError(Exception):
    def __init__(self, message, doi):
        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        # Store DOI as error in object
        # @TODO do something with error_doi?
        self.error_doi = doi
