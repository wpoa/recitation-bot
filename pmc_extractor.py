#!/usr/bin/env python
# -*- coding: utf-8 -*-
#all credits to https://github.com/wpoa/open-access-media-importer/

from datetime import date
from os import listdir, path
from sys import stderr
from xml.etree.ElementTree import ElementTree
from collections import defaultdict
import json
import sys

def extract_metadata(target_nxml):
    """
    Get as much metadata as we can from an nxml
    """
    tree = ElementTree()
    tree.parse(target_nxml)

    metadata = dict()
    metadata['doi'] = _get_article_doi(tree)
    metadata['pmcid'] = _get_pmcid(tree)
    metadata['pmid'] = _get_pmid(tree)
    metadata['article-contrib-authors'] = _get_article_contrib_authors(tree)
    metadata['article-title'] = _get_article_title(tree)
    metadata['article-abstract'] = _get_article_abstract(tree)
    metadata['journal-title'] = _get_journal_title(tree)
    metadata['article-year'], metadata['article-month'], metadata['article-day'] = _get_article_date(tree)
    metadata['article-url'] = _get_article_url(tree)
    metadata['article-license-url'], metadata['article-license-text'], metadata['article-copyright-statement'] = _get_article_licensing(tree)
    metadata['article-copyright-holder'] = _get_article_copyright_holder(tree)
    metadata['article-categories'] = _get_article_categories(tree)
    metadata['image_captions'] = _get_image_captions(tree)
    metadata['supplement_captions'] = _get_supplementary_captions(tree)
    metadata['images'] = dict(list(metadata['image_captions'].items()) + list(metadata['supplement_captions'].items()) )
    metadata['supplementary-materials'] = _get_supplementary_materials(tree)
    metadata['inline_formulae'] = _get_filenames_2tags(tree, 'inline-formula', 'inline-graphic')
    metadata['display_formulae'] = _get_filenames_2tags(tree, 'disp-formula', 'graphic')
    metadata['equations'] = dict(list(metadata['inline_formulae'].items()) + list(metadata['display_formulae'].items()) )
    metadata['tables'] = _get_filenames_2tags(tree, 'alternatives', 'graphic')

    return metadata


def _strip_whitespace(text):
    """
    Strips leading and trailing whitespace for multiple lines.
    """
    text = '\n'.join(
        [line.strip() for line in text.splitlines()]
    )
    return text.strip('\n')


def _get_filenames_2tags(tree, tag1, tag2):
    """
    Given an ElementTree returns iamges as a
    dictionary containing, file_names.
    """
    return_captions = defaultdict(dict)
    for t1 in tree.iter(tag1):
        t2 = t1.find(tag2)
        file_name = t2.attrib['{http://www.w3.org/1999/xlink}href']
        return_captions[file_name]['caption'] = file_name #we could use a list but leaving for generality in the future since the other images return a dict
    return return_captions


def _get_image_captions(tree):
    """
    Given an ElementTree returns iamges as a
    dictionary containing, file_name label and caption.
    """
    fig_captions = defaultdict(dict)
    for fig in tree.iter('fig'):
        graphic = fig.find('graphic')
        if graphic is not None: #adding an extra check here because sometimes graphic is None
            file_name = graphic.attrib['{http://www.w3.org/1999/xlink}href']
            label_text = ''
            label = fig.find('label')
            if label is not None:
                label_text = label.text
                fig_captions[file_name]['label'] = label_text
            caption = fig.find('caption/p')
            caption_text = ''
            if caption is not None:
                caption_text = _strip_whitespace(''.join(caption.itertext()))
            fig_captions[file_name]['caption'] = caption_text
    return fig_captions

def _get_supplementary_captions(tree):
    """
    Given an ElementTree returns media as a
    dictionary containing, file_name label and caption.
    """
    fig_captions = defaultdict(dict)
    for fig in tree.iter('supplementary-material'):
        graphic = fig.find('media')
        file_name = graphic.attrib['{http://www.w3.org/1999/xlink}href']
        label_text = ''
        label = fig.find('label')
        if label is not None:
            label_text = label.text
            fig_captions[file_name]['label'] = label_text
        caption = fig.find('caption/p')
        caption_text = ''
        if caption is not None:
            caption_text = _strip_whitespace(''.join(caption.itertext()))
        fig_captions[file_name]['caption'] = caption_text
    return fig_captions

def _get_article_categories(tree):
    """
    Given an ElementTree, return (some) article categories.
    """
    categories = []
    article_categories = ElementTree(tree).find('.//*article-categories')
    for subject_group in article_categories.iter('subj-group'):
        try:
            if subject_group.attrib['subj-group-type'] == 'heading':
                continue
        except KeyError:  # no attribute “subj-group-type”
            pass
        for subject in subject_group.iter('subject'):
            if subject.text is None:
                continue
            if '/' in subject.text:
                category_text = subject.text.split('/')[-1]
            else:
                category_text = subject.text
            if ' ' in category_text and not 'and' in category_text and \
                category_text not in categories:
                categories.append(category_text)
    keywords = []
    article_keywords = ElementTree(tree).find('.//*kwd-group')
    if article_keywords != None:
        for keyword in article_keywords.iter('kwd'):
            if keyword.text is None:
                continue
            keywords.append(keyword.text)
    return categories+keywords

def _get_article_contrib_authors(tree):
    """
    Given an ElementTree, returns article authors in a format suitable for citation.
    """
    authors = []
    front = ElementTree(tree).find('front')
    for contrib in front.iter('contrib'):
        if contrib.attrib['contrib-type'] != 'author':
            continue
        contribTree = ElementTree(contrib)
        try:
            surname = contribTree.find('name/surname').text
        except AttributeError:  # author is not a natural person
            try:
                citation_name = contribTree.find('collab').text
                if citation_name is not None:
                    authors.append(citation_name)
                continue
            except AttributeError:  # name has no immediate text node
                continue

        try:
            given_names = contribTree.find('name/given-names').text
            citation_name = ' '.join([surname, given_names[0]])
        except AttributeError:  # no given names
            citation_name = surname
        except TypeError:  # also no given names
            citation_name = surname
        if citation_name is not None:
            authors.append(citation_name)

    return ', '.join(authors)

def _get_article_title(tree):
    """
    Given an ElementTree, returns article title.
    """
    title = ElementTree(tree).find('front/article-meta/title-group/article-title')
    if title is None:
        title = ElementTree(tree).find('front/article-meta/article-categories/subj-group/subject')
    return ''.join(title.itertext())

def _get_article_abstract(tree):
    """
    Given an ElementTree, returns article abstract.
    """
    for abstract in ElementTree(tree).iterfind('.//*abstract'):
        if 'abstract-type' in abstract.attrib:  # toc or summary
            continue
        else:
            return _strip_whitespace(''.join(abstract.itertext()))
    return None

def _get_journal_title(tree):
    """
    Given an ElementTree, returns journal title.
    """
    front = ElementTree(tree).find('front')
    for journal_meta in front.iter('journal-meta'):
        for journal_title in journal_meta.iter('journal-title'):
            title = journal_title.text
            # take only the part before the colon, strip whitespace
            title = title.split(':')[0].strip()
            title = title.replace('PLoS', 'PLOS').replace('PloS', 'PLOS')
            return title

def _get_article_date(tree):
    """
    Given an ElementTree, returns article date as list of integers in
    the format [year, month, day].
    """
    article_meta = tree.find('front/article-meta')
    for pub_date in article_meta.iter('pub-date'):
        year = int(pub_date.find('year').text)
        try:
            month = int(pub_date.find('month').text)
        except AttributeError:
            return year, None, None
        try:
            day = int(pub_date.find('day').text)
        except AttributeError:
            return year, month, None
        return year, month, day
    raise RuntimeError('No date information found.')

def _get_article_url(tree):
    """
    Given an ElementTree, returns article URL.
    """
    doi = _get_article_doi(tree)
    if doi:
        return 'http://dx.doi.org/' + doi

open_license_dict_path = './Open-License-Dictionary/'

license_url_equivalents = json.load(open(open_license_dict_path+'open_license_dictionary.json','r'))

copyright_statement_url_equivalents = json.load(open(open_license_dict_path+'copyright_dictionary.json','r'))

license_url_fixes = {
    'http://creativecommons.org/Licenses/by/2.0': 'http://creativecommons.org/licenses/by/2.0/',
    '(http://creativecommons.org/licenses/by/2.0)': 'http://creativecommons.org/licenses/by/2.0/',
    'http://(http://creativecommons.org/licenses/by/2.0)': 'http://creativecommons.org/licenses/by/2.0/',
    'http://creativecommons.org/licenses/by/2.0': 'http://creativecommons.org/licenses/by/2.0/',
    'http://creativecommons.org/licenses/by/3.0': 'http://creativecommons.org/licenses/by/3.0/',
    'http://creativecommons.org/licenses/by/4.0': 'http://creativecommons.org/licenses/by/4.0/',
    'http://creativecommons.org/licenses/by/4.0/legalcode': 'http://creativecommons.org/licenses/by/4.0/'
}

def _get_article_licensing(tree):
    """
    NOTE!!!! ‽!?!⸘ the variable name 'licence' is a reserved word (who would have thought⸘)
    so so ive renamed some all the vars in this block to use the Aussie spelling. but i have not changed the outised of this block since other functions may depend on it. 

    Given an ElementTree, returns article licence URL.
    """
    licence_text = None
    licence_url = None
    copyright_statement_text = None

    licence = tree.find(u'front//*license')
    copyright_statement = tree.find(u'front//*copyright-statement')

    code = 'utf-8'

    def _get_text_from_element(element):
        text = ' '.join(element.itertext()).encode(code).decode(code)  # clean encoding
        text = ' '.join(text.split())  # clean whitespace
        return text

    if licence is not None:
        try:
            licence_url = licence.attrib[u'{http://www.w3.org/1999/xlink}href']
        except KeyError: # licence URL is possibly in <ext-link> element
            try:
                ext_link = licence.find(u'license-p/ext-link')
                if ext_link is not None:
                    licence_url = \
                        ext_link.attrib[u'{http://www.w3.org/1999/xlink}href']
            except KeyError: # licence statement maybe is in plain text
                pass
        try:
            licence_text = _get_text_from_element(licence)
        except:
            pass
            #logging.error('not sure what to do here')
    elif copyright_statement is not None:
        copyright_statement_text = _get_text_from_element(copyright_statement)
    else:
        #logging.error('No <license> or <copyright-statement> element found in XML.')
        return None, None, None

    if licence_url is None:
        if licence_text is not None:
           try:
               licence_url = license_url_equivalents[licence_text.encode(code).decode(code)]
           except KeyError:
             #logging.error('Unknown licence: %s', licence_text)
             pass

        elif copyright_statement_text is not None:
            copyright_statement_found = False
            for text in list(copyright_statement_url_equivalents.keys()):
                if copyright_statement_text.endswith(text.encode(code).decode(code)):
                    licence_url = copyright_statement_url_equivalents[text.encode(code).decode(code)]
                    copyright_statement_found = True
                    break
            if not copyright_statement_found:
                #logging.error('Unknown copyright statement: %s', copyright_statement_text)
                pass

    def _fix_licence_url(licence_url):
        if licence_url in list(license_url_fixes.keys()):
            return license_url_fixes[licence_url]
        return licence_url

    if licence_text is not None:
        licence_text = licence_text.encode(code).decode(code)

    if copyright_statement_text is not None:
        copyright_statement_text = copyright_statement_text.encode(code).decode(code)

    if licence_url is not None:
        return _fix_licence_url(licence_url), licence_text, copyright_statement_text
    else:
        return None, licence_text, copyright_statement_text

def _get_article_copyright_holder(tree):
    """
    Given an ElementTree, returns article copyright holder.
    """
    copyright_holder = tree.find(
        'front/article-meta/permissions/copyright-holder'
    )
    try:
        copyright_holder = copyright_holder.text
        if copyright_holder is not None:
            return copyright_holder
    except AttributeError:  # no copyright_holder known
        pass

    copyright_statement = tree.find('.//*copyright-statement')
    try:
        copyright_statement = copyright_statement.text
        if copyright_statement is not None:
            return copyright_statement.split('.')[0] + '.'
    except AttributeError:
        pass

    return None

def _get_supplementary_materials(tree):
    """
    Given an ElementTree, returns a list of article supplementary materials.
    """
    materials = []
    for sup in tree.iter('supplementary-material'):
        material = _get_supplementary_material(tree, sup)
        if material is not None:
            materials.append(material)
    for fig in tree.iter('fig'):
        material = _get_supplementary_material(tree, fig)
        if material is not None:
            materials.append(material)
    return materials

def _get_supplementary_material(tree, sup):
    """
    Given an ElementTree returns supplementary materials as a
    dictionary containing url, mimetype and label and caption.
    """
    result = {}
    sup_tree = ElementTree(sup)

    label = sup_tree.find('label')
    result['label'] = ''
    if label is not None:
        result['label'] = label.text

    title = sup_tree.find('caption/title')
    result['title'] = ''
    if title is not None:
        title = _strip_whitespace(' '.join(title.itertext()))
        result['title'] = title

    caption = sup_tree.find('caption')
    result['caption'] = ''
    if caption is not None:
        caption_without_title = []
        for node in caption:
            if node.tag != 'title':
                caption_without_title.append(''.join(node.itertext()))
        caption = _strip_whitespace('\n'.join(caption_without_title))
        # remove file size and type information, e.g. “(1.3 MB MPG)”
        lastline = caption.split('\n')[-1]
        if lastline.startswith('(') and lastline.endswith(')'):
            caption = ' '.join(caption.split('\n')[:-1])
        assert 'Click here' not in caption
        result['caption'] = caption

    media = sup_tree.find('media')
    if media is not None:
        try:
            result['mimetype'] = media.attrib['mimetype']
            result['mime-subtype'] = media.attrib['mime-subtype']
            result['href'] = media.attrib['{http://www.w3.org/1999/xlink}href']
        except KeyError:
            result['mimetype'] = ''
            result['mime-subtype'] = ''
            result['href'] = ''
        result['url'] = _get_supplementary_material_url(
            _get_pmcid(tree),
            result['href']
        )
        return result

def _get_pmcid(tree):
    """
    Given an ElementTree, returns PubMed Central ID.
    """
    front = ElementTree(tree).find('front')
    for article_id in front.iter('article-id'):
        if article_id.attrib['pub-id-type'] == 'pmc':
            return article_id.text

def _get_pmid(tree):
    """
    Given an ElementTree, returns PubMed Central ID.
    """
    front = ElementTree(tree).find('front')
    for article_id in front.iter('article-id'):
        if article_id.attrib['pub-id-type'] == 'pmid':
            return article_id.text

def _get_article_doi(tree):
    """
    Given an ElementTree, returns DOI.
    """
    front = ElementTree(tree).find('front')
    for article_id in front.iter('article-id'):
        try:
            if article_id.attrib['pub-id-type'] == 'doi':
                return article_id.text
        except KeyError:
            pass

def _get_supplementary_material_url(pmcid, href):
    """
    This function creates absolute URIs for supplementary materials,
    using a PubMed Central ID and a relative URI.
    """
    return str('http://www.ncbi.nlm.nih.gov/pmc/articles/PMC' + pmcid +
        '/bin/' + href)

if __name__ == '__main__':
    #test that we can pull from the Open License Dict well
    print(('Open license loaded:', len(license_url_equivalents)))
    print(('Copyright licenses loaded:', len(copyright_statement_url_equivalents)))
    target_nxml = sys.argv[1]
    metadata = extract_metadata(target_nxml)
    for k,v in metadata.items():
        if k in ['article-license-text']:
            print(k)
            print(v)
