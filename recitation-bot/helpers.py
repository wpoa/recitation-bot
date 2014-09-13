# -*- coding: utf-8 -*-
import os

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
    for extension in ['.jpg','.png','.jpeg', 'JPG', '.JPEG', '.PNG', '.tif', '.tiff', '.TIF', '.TIFF', '.svg', '.SVG']:
        image_file = image + extension
        qualified_image_location = os.path.join(qualified_article_dir, image_file)
        print(qualified_image_location)
        if os.path.isfile(qualified_image_location):
            return image_file, qualified_image_location
        else:
            continue
#this means no valid extension was found and returned
    return False, False #two falses so we don't break a caller expecting muliple assignment return
