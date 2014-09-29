# -*- coding: utf-8 -*-
import os
import logging
import requests

logging.basicConfig(filename='/data/project/recitation-bot/public_html/recitation-bot-log.html', format='%(asctime)s %(message)s', level=logging.DEBUG)

#want to make the name commons-compatible in the way that OAMI does
def harmonizing_name(image_name, article_title):
    '''Copy Pasta-ed from open access media importer to get it the same'''
    dirty_prefix = article_title
    dirty_prefix = dirty_prefix.replace('\n', '')
    dirty_prefix = ' '.join(dirty_prefix.split()) # remove multiple spaces
    forbidden_chars = u"""?,;:^/!<>"`'±#[]|{}ʻʾʿ᾿῾‘’“”"""
    for character in forbidden_chars:
        dirty_prefix = dirty_prefix.replace(character, '')
    # prefix is first hundred chars of title sans forbidden characters
    prefix = '-'.join(dirty_prefix[:100].split(' '))
    # if original title is longer than cleaned up title, remove last word
    if len(dirty_prefix) > len(prefix):
        prefix = '-'.join(prefix.split('-')[:-1])
    if prefix[-1] != '-':
        prefix += '-'
    return prefix + image_name


def title_cleaner(article_title):
    #reusing some of the harmonizer code
    
    '''Copy Pasta-ed from open access media importer to get it the same'''
    dirty_prefix = article_title
    dirty_prefix = dirty_prefix.replace('\n', ' ')
    dirty_prefix = ' '.join(dirty_prefix.split()) # remove multiple spaces
    forbidden_chars = u"""?,;:^/!<>"`'±#[]|{}ʻʾʿ᾿῾‘’“”"""
    for character in forbidden_chars:
        dirty_prefix = dirty_prefix.replace(character, '')
    return dirty_prefix


def find_right_extension(image, qualified_article_dir):
    '''this is a helper to get determine what extension to use'''
    EXTENSIONS = ['jpg', 'png','jpeg', 'JPG', 'JPEG', 'Jpeg', 'PNG', 'tif', 'tiff', 'TIF', 'TIFF', 'svg', 'SVG']
    #first check if we were give an image file as is the case for supplemental images
    if image.split('.')[-1] in EXTENSIONS:
        qualified_image_location = os.path.join(qualified_article_dir, image)
        if os.path.isfile(qualified_image_location):
            return image, qualified_image_location
    for extension in EXTENSIONS:
        image_file = image + '.' + extension
        qualified_image_location = os.path.join(qualified_article_dir, image_file)
        if os.path.isfile(qualified_image_location):
            return image_file, qualified_image_location
        else:
            continue
#this means no valid extension was found and returned
    return False, False #two falses so we don't break a caller expecting muliple assignment return

def find_file_in_commons(filename):
    # Use mediawiki search api to find file with unique string (doi href)
    results = requests.get('https://commons.wikimedia.org/w/api.php?' +
                           'action=query' +
                           '&list=search' +
                           '&srnamespace=6' +
                           '&prop=imageinfo' +
                           '&srsearch=' + filename +
                           '&srlimit=1' +
                           '&format=json')
    if results.json()[u'query'][u'searchinfo'][u'totalhits'] == 1:
        return results.json()[u'query'][u'search'][0][u'title']
    else:
        return False
