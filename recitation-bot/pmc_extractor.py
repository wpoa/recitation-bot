#!/usr/bin/env python
# -*- coding: utf-8 -*-
#all credits to https://github.com/wpoa/open-access-media-importer/

from datetime import date
from os import listdir, path
from sys import stderr
from xml.etree.ElementTree import ElementTree
from collections import defaultdict

def extract_metadata(target_nxml):
    """
    Get as much metadata as we can from an nxml
    """
    tree = ElementTree()
    tree.parse(target_nxml)

    metadata = dict()
    metadata['doi'] = _get_article_doi(tree)
    metadata['article-contrib-authors'] = _get_article_contrib_authors(tree)
    metadata['article-title'] = _get_article_title(tree)
    metadata['article-abstract'] = _get_article_abstract(tree)
    metadata['journal-title'] = _get_journal_title(tree)
    metadata['article-year'], metadata['article-month'], metadata['article-day'] = _get_article_date(tree)
    metadata['article-url'] = _get_article_url(tree)
    metadata['article-license-url'], metadata['article-license-text'], metadata['article-copyright-statement'] = _get_article_licensing(tree)
    metadata['article-copyright-holder'] = _get_article_copyright_holder(tree)
    metadata['article-categories'] = _get_article_categories(tree)
    metadata['images'] = _get_image_captions(tree)
    #metadata['supplementary-materials'] = _get_supplementary_materials(tree)


    return metadata

def _strip_whitespace(text):
    """
    Strips leading and trailing whitespace for multiple lines.
    """
    text = '\n'.join(
        [line.strip() for line in text.splitlines()]
    )
    return text.strip('\n')

def _get_image_captions(tree):
    """
    Given an ElementTree returns iamges as a
    dictionary containing, file_name label and caption.
    """
    for fig in tree.iter('fig'):
        fig_captions = defaultdict(dict)
        for fig in tree.iter('fig'):
            graphic = fig.find('graphic')
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
    raise RuntimeError, 'No date information found.'

def _get_article_url(tree):
    """
    Given an ElementTree, returns article URL.
    """
    doi = _get_article_doi(tree)
    if doi:
        return 'http://dx.doi.org/' + doi

license_url_equivalents = {
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution License, ( http://creativecommons.org/licenses/by/3.0/ ) which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
    'This is an open-access article, free of all copyright, and may be freely reproduced, distributed, transmitted, modified, built upon, or otherwise used by anyone for any lawful purpose. The work is made available under the Creative Commons CC0 public domain dedication.': 'http://creativecommons.org/publicdomain/zero/1.0/',
    '>This work is licensed under a Creative Commons Attribution NonCommercial 3.0 License (CC BY-NC 3.0). Licensee PAGEPress, Italy': None,
     'Available freely online through the author-supported open access option.': None,
     'Distributed under the Hogrefe OpenMind License [ http://dx.doi.org/10.1027/a000001]': 'http://dx.doi.org/10.1027/a000001',
     'Freely available online through the American Journal of Tropical Medicine and Hygiene Open Access option.': None,
     'License information: This is an open-access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0',
     'Open Access': None,
     'Readers may use this article as long as the work is properly cited, the use is educational and not for profit, and the work is not altered. See http://creativecommons.org/licenses/by -nc-nd/3.0/ for details.': None,
     'Readers may use this article as long as the work is properly cited, the use is educational and not for profit, and the work is not altered. See http://creativecommons.org/licenses/by-nc-nd/3.0/ for details.': None,
     'Readers may use this article as long as the work is properly cited, the use is educational and not for profit,and the work is not altered. See http://creativecommons.org/licenses/by-nc-nd/3.0/ for details.': None,
     'Readers may use this article aslong as long as the work is properly cited, the use is educational and not for profit, and the work is not altered. See http://creativecommons.org/licenses/by-nc-nd/3.0/ for details.': None,
     'The authors have paid a fee to allow immediate free access to this article.': None,
     'The online version of this article has been published under an open access model, users are entitle to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and the European Society for Medical Oncology are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org': None,
     'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org': None,
     'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org.': None,
     'The online version of this article has been published under an open access model. users are entitle to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and the European Society for Medical Oncology are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org': None,
     'The online version of this article is published within an Open Access environment subject to the conditions of the Creative Commons Attribution-NonCommercial-ShareAlike licence < http://creativecommons.org/licenses/by-nc-sa/2.5/>. The written permission of Cambridge University Press must be obtained for commercial re-use': None,
     'The online version of this article is published within an Open Access environment subject to the conditions of the Creative Commons Attribution-NonCommercial-ShareAlike licence < http://creativecommons.org/licenses/by-nc-sa/2.5/>. The written permission of Cambridge University Press must be obtained for commercial re-use.': None,
     'Thi is an open access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This article is an open-access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ ).': 'http://creativecommons.org/licenses/by/3.0/',
     'This article is in the public domain.': 'http://creativecommons.org/licenses/publicdomain/',
     'This article, manuscript, or document is copyrighted by the American Psychological Association (APA). For non-commercial, education and research purposes, users may access, download, copy, display, and redistribute this article or manuscript as well as adapt, translate, or data and text mine the content contained in this document. For any such use of this document, appropriate attribution or bibliographic citation must be given. Users should not delete any copyright notices or disclaimers. For more information or to obtain permission beyond that granted here, visit http://www.apa.org/about/copyright.html.': None,
     'This document may be redistributed and reused, subject to certain conditions .': None,
     'This document may be redistributed and reused, subject to www.the-aps.org/publications/journals/funding_addendum_policy.htm .': None,
     'This is a free access article, distributed under terms ( http://www.nutrition.org/publications/guidelines-and-policies/license/ ) which permit unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is a free access article, distributed under terms that permit unrestricted noncommercial use, distribution, and reproduction in any medium, provided the original work is properly cited. http://www.nutrition.org/publications/guidelines-and-policies/license/ .': None,
     "This is an Open Access article distributed under the terms and of the American Society of Tropical Medicine and Hygiene's Re-use License which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.": None,
     "This is an Open Access article distributed under the terms of the American Society of Tropical Medicine and Hygiene's Re-use License which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.": None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License ( http://creativecommons.org/licenses/by/2.0 ), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License ( http://creativecommons.org/licenses/by/3.0 ), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License (<url>http://creativecommons.org/licenses/by/2.0</url>), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License (http://creativecommons.org/licenses/by/2.0), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0 ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/uk/ ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5 ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5/ ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5/uk/ ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/3.0 ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/3.0/ ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/3.0/us/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses?by-nc/2.5 ), which permits unrestricted non-commercial use distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial Share Alike License ( http://creativecommons.org/licenses/by-nc-sa/3.0 ), which permits unrestricted non-commercial use, distribution and reproduction in any medium provided that the original work is properly cited and all further distributions of the work or adaptation are subject to the same Creative Commons License terms': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial Share Alike License ( http://creativecommons.org/licenses/by-nc-sa/3.0 ), which permits unrestricted non-commercial use, distribution and reproduction in any medium provided that the original work is properly cited and all further distributions of the work or adaptation are subject to the same Creative Commons License terms.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution licence which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution-Noncommercial License ( http://creativecommons.org/licenses/by-nc/3.0/ ), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited. Information for commercial entities is available online ( http://www.chestpubs.org/site/misc/reprints.xhtml ).': None,
     'This is an Open Access article which permits unrestricted noncommercial use, provided the original work is properly cited.': None,
     'This is an Open Access article which permits unrestricted noncommercial use, provided the original work is properly cited. Clinical Ophthalmology 2011:5 101\xe2\x80\x93108': None,
     'This is an Open Access article: verbatim copying and redistribution of this article are permitted in all media for any purpose': None,
     'This is an open access article distributed under the Creative Commons Attribution License, in which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0',
     'This is an open access article distributed under the Creative Commons Attribution License, which permits unrestricted use, distribution and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open access article distributed under the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open access article distributed under the Creative Commons attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open access article distributed under the terms of the Creative Commons Attribution License ( http://creativecommons.org/licenses/by/2.0 ), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0',
     'This is an open access article distributed under the terms of the Creative Commons Attribution License ( http://www.creativecommons.org/licenses/by/2.0 ) which permits unrestricted use, distribution and reproduction provided the original work is properly cited.': 'http://www.creativecommons.org/licenses/by/2.0',
     'This is an open access article distributed under the terms of the Creative Commons Attribution License (<url>http://creativecommons.org/licenses/by/2.0</url>), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0',
     'This is an open access article distributed under the terms of the Creative Commons Attribution License (http://creativecommons.org/licenses/by/2.0), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0',
     'This is an open access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open access article distributed under theCreative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open access article. Unrestricted non-commercial use is permitted provided the original work is properly cited.': None,
     'This is an open access paper distributed under the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0',
     'This is an open-access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original author and source are credited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open-access article distributed under the terms of the Creative Commons Attribution Non-commercial License, which permits use, distribution, and reproduction in any medium, provided the original work is properly cited, the use is non commercial and is otherwise in compliance with the license. See: http://creativecommons.org/licenses/by-nc/2.0/ and http://creativecommons.org/licenses/by-nc/2.0/legalcode .': None,
     'This research note is distributed under the Commons Attribution-Noncommercial 3.0 License.': None,
     'This research note is distributed under the Creative Commons Attribution 3.0 License.': 'http://creativecommons.org/licenses/by/3.0',
     'This work is licensed under a Creative Commons Attr0ibution 3.0 License (by-nc 3.0). Licensee PAGE Press, Italy': None,
     'This work is licensed under a Creative Commons Attribution 3.0 License (by-nc 3.0) Licensee PAGEPress, Italy': None,
     'This work is licensed under a Creative Commons Attribution 3.0 License (by-nc 3.0). Licensee PAGE Press, Italy': None,
     'This work is licensed under a Creative Commons Attribution 3.0 License (by-nc 3.0). Licensee PAGEPress, Italy': None,
     'This work is licensed under a Creative Commons Attribution NonCommercial 3.0 License (CC BY-NC 3.0). Licensee PAGEPress srl, Italy': None,
     'This work is licensed under a Creative Commons Attribution NonCommercial 3.0 License (CC BY-NC 3.0). Licensee PAGEPress, Italy': None,
     'This work is subject to copyright. All rights are reserved, whether the whole or part of the material is concerned, specifically the rights of translation, reprinting, reuse of illustrations, recitation, broadcasting, reproduction on microfilm or in any other way, and storage in data banks. Duplication of this publication or parts thereof is permitted only under the provisions of the German Copyright Law of September 9, 1965, in its current version, and permission for use must always be obtained from Springer-Verlag. Violations are liable for prosecution under the German Copyright Law.': None,
     'This work is subject to copyright. All rights are reserved, whether the whole or part of the material is concerned, specifically the rights of translation, reprinting, reuse of illustrations, recitation, broadcasting, reproduction on microfilm or in any other way, and storage in data banks. Duplication of this publication or parts thereof is permitted only under the provisions of the German Copyright Law of September 9, in its current version, and permission for use must always be obtained from Springer-Verlag. Violations are liable for prosecution under the German Copyright Law.': None,
     'Users may view, print, copy, download and text and data- mine the content in such documents, for the purposes of academic research, subject always to the full Conditions of use: http://www.nature.com/authors/editorial_policies/license.html#terms': None,
     'creative commons': None,
     '\xc2\xa7 The authors have paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\x96 The authors have paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\x96The authors have paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\xa0 The author has paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\xa0 The authors have paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\xa0The authors have paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\xa1 The authors have paid a fee to allow immediate free access to this article': None,
     '\xe2\x80\xa1 The authors have paid a fee to allow immediate free access to this article.': None,
     '\xe2\x80\xa1The authors have paid a fee to allow immediate free access to this article.': None,
     "You are free to share–to copy, distribute and transmit the work, under the following conditions: Attribution :  You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial :  You may not use this work for commercial purposes. No derivative works :  You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode. Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this license impairs or restricts the author's moral rights.": None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited. This paper is available online free of all access charges (see http://jxb.oxfordjournals.org/open_access.html for further details)': None,
     'Royal College of Psychiatrists, This paper accords with the Wellcome Trust Open Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/Wellcome%20Trust%20licence.pdf' : None,
     'This is an open access article distributed under the Creative Commons Attribution License,which permits unrestricted use,distribution,and reproduction in any medium,provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This paper is an open-access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ ).': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an Open Access articlewhich permits unrestricted noncommercial use, provided the original work is properly cited.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-commercial License ( http://creativecommons.org/licences/by-nc/2.0/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited. This paper is available online free of all access charges (see http://jxb.oxfordjournals.org/open_access.html for further details)': None,
     'This is an open access article distributed under the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work are properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License (<url>http://creativecommons.org/licenses/by/2.0</url>), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited': 'http://creativecommons.org/licenses/by/2.0',
     'This work is licensed under a Creative Commons Attribution 3.0 License (by-nc 3.0).': None,
     'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oupjournals.org': None,
     "Author's Choice - Final Version Full Access NIH Funded Research - Final Version Full Access Creative Commons Attribution Non-Commercial License applies to Author Choice Articles": None,
     'The online version of this article has been published under an open access model. users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commerical purposes provided that: the original authorship is properly and fully attributed; the Journal and the Guarantors of Brain are attributed as the original place of publication with the correction citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org.': None,
     "You are free to share - to copy, distribute and transmit the work, under the following conditions: Attribution: You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial: You may not use this work for commercial purposes. No derivative works: You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode . Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this license impairs or restricts the author's moral rights.": None,
     'Open access articles can be viewed online without a subscription.': None,
     '‡ The authors have paid a fee to allow immediate free access to this work.': None,
     'Published under the CreativeCommons Attribution-NonCommercial-NoDerivs 3.0 License .': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/uk/ ) which permits unrestricted non-commercial use distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/. )': 'http://creativecommons.org/licenses/by/3.0/',
     'This work is licensed under a Creative Commons Attribution 3.0 License (by-nc 3.0)': None,
     "Author's Choice —Final version full access. NIH Funded Research - Final version full access. Creative Commons Attribution Non-Commercial License applies to Author Choice Articles": None,
     'This is an open-access article, which permits unrestricted use, distribution, and reproduction in any medium, for non-commercial purposes, provided the original author and source are credited.': None,
     'This article is an open-access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ )': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial No Derivatives License ( http://creativecommons.org/licenses/by-nc-nd/3.0/ ), which permits for noncommercial use, distribution, and reproduction in any medium, provided the original work is properly cited and is not altered in any way.': None,
     'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license http://creativecommons.org/licenses/by/3.0/ .': 'http://creativecommons.org/licenses/by/3.0/',
     "You are free to share–to copy, distribute and transmit the work, under the following conditions: Attribution :  You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial :  You may not use this work for commercial purposes. No derivative works :  You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode . Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this license impairs or restricts the author's moral rights.": None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/y-nc/2.0/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This work is licensed under a Creative Commons Attribution Noncommercial 3.0 License (CC BYNC 3.0). Licensee PAGEPress, Italy': None,
     'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org Published by Oxford University Press on behalf of the International Epidemiological Association': None,
     'This is an open access article distributed under the Creative Commons Attribution License which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     "You are free to share - to copy, distribute and transmit the work, under the following conditions: Attribution:   You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial:   You may not use this work for commercial purposes. No derivative works:   You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode . Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this license impairs or restricts the author's moral rights.": None,
     'This article is distributed under the terms of an Attribution–Noncommercial–Share Alike–No Mirror Sites license for the first six months after the publication date (see http://www.jem.org/misc/terms.shtml ). After six months it is available under a Creative Commons License (Attribution–Noncommercial–Share Alike 3.0 Unported license, as described at http://creativecommons.org/licenses/by-nc-sa/3.0/ ).': None,
     'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for noncommercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/byc/2.5 ), which permits unrestricted nonommercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press and The Japanese Society for Immunology are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org': None,
     '# The authors have paid a fee to allow immediate free access to this paper.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License (http://creativecommons.org/licenses/by-nc/2.0/uk/) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This work is licensed under a Creative Commons Attribution NonCommercial 3.0 License (CC BYNC 3.0). LicenseePAGEPress, Italy': None,
     'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ ).': 'http://creativecommons.org/licenses/by/3.0/',
     "Author's Choice - Final Version Full Access Creative Commons Attribution Non-Commercial License applies to Author Choice Articles": None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited. This paper is available online free of all access charges (see http://jxb.oxfordjournals.org/open_access.html for further details)': None,
     'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ )': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an open access article distributed under the Creative Commons Attribution License, that permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ .)': 'http://creativecommons.org/licenses/by/3.0/',
     "Author's Choice —Final version full access. Creative Commons Attribution Non-Commercial License applies to Author Choice Articles": None,
     '¶ The authors have paid a fee to allow immediate free access to this article.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5 ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited. This paper is available online free of all access charges (see http://jxb.oxfordjournals.org/open_access.html for further details)': None,
     'This article is distributed under the terms of an Attribution–Noncommercial–Share Alike–No Mirror Sites license for the first six months after the publication date (see http://www.jcb.org/misc/terms.shtml ). After six months it is available under a Creative Commons License (Attribution–Noncommercial–Share Alike 3.0 Unported license, as described at http://creativecommons.org/licenses/by-nc-sa/3.0/ ).': None,
     '99This is an open access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     "You are free to share–to copy, distribute and transmit the work, under the following conditions: Attribution :  You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial :  You may not use this work for commercial purposes. No derivative works :  You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode. Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this lincense impairs or restricts the author's moral rights.": None,
     'This is an open access article distributed under the terms of the creative commons attribution license, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'Royal College of Psychiatrists, This paper accords with the NIH Public Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/NIH%20licence%20agreement.pdf Royal College of Psychiatrists, This paper accords with the Wellcome Trust Open Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/Wellcome%20Trust%20licence.pdf': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/uk/> ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
     'This article is an Open Access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/ ).': 'http://creativecommons.org/licenses/by/3.0/',
     'Available online without subscription through the open access option.': None,
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This article is distributed under the terms of an Attribution–Noncommercial–Share Alike–No Mirror Sites license for the first six months after the publication date (see http://www.jgp.org/misc/terms.shtml ). After six months it is available under a Creative Commons License (Attribution–Noncommercial–Share Alike 3.0 Unported license, as described at http://creativecommons.org/licenses/by-nc-sa/3.0/ ).': None,
     'This is an open access article distributed under the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original paper is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This is an Open Access article distributed under the terms of the Creative Commons Attribution License ( http://creativecommons.org/licenses/by/3.0/ ), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
     'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license ( http://creativecommons.org/licenses/by/3.0/': 'http://creativecommons.org/licenses/by/3.0/',
     "You are free to share - to copy, distribute and transmit the work, under the following conditions: Attribution:   You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial:   You may not use this work for commercial purposes. No derivative works:   You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode. Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this license impairs or restricts the author's moral rights.": None,
    "This is an Open Access article: verbatim copying and redistribution of this article are permitted in all media for any purpose, provided this notice is preserved along with the article's original URL.": None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5 ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'This article is an open-access article distributed under the terms and conditions of the Creative Commons Attribution license http://creativecommons.org/licenses/by/3.0/ .': 'http://creativecommons.org/licenses/by/3.0/',
    'Published under the CreativeCommons Attribution NonCommercial-NoDerivs 3.0 License .': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/3.0 ), which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited. This paper is available online free of all access charges (see http://jxb.oxfordjournals.org/open_access.html for further details)': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-ommercial License ( http://creativecommons.org/licenses/byc/2.5 ), which permits unrestricted nonommercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'This paper accords with the Wellcome Trust Open Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/Wellcome%20Trust%20licence.pdf': None,
    'This paper accords with the NIH Public Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/NIH%20licence%20agreement.pdf This paper accords with the Wellcome Trust Open Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/Wellcome%20Trust%20licence.pdf': None,
    'This article is an Open Access article distributed under the terms and conditions of the Creative Commons Attribution license http://creativecommons.org/licenses/by/3.0/ .': 'http://creativecommons.org/licenses/by/3.0/',
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses?by-nc/2.0/uk/ ) which permits unrestricted non-commercial use distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'This is an Open Access article distributed under the terms of the Creative Commons-Attribution Noncommercial License ( http://creativecommons.org/licenses/by-nc/2.0/ ), which permits unrestricted noncommercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'Creative Commons Attribution Non-Commercial License applies to Author Choice Articles': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5 ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited. This paper is available online free of all access charges (see http://jxb.oxfordjournals.org/open_access.html for further details)': None,
    'This is an open access article distributed under the terms of the creative commons attribution license, which permits unrestricteduse, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
    'available online without subscription through the open access option.': None,
    "Author's Choice": None,
    '# The authors have paid a fee to allow immediate free access to this article.': None,
    'Open Access articles can be viewed online without a subscription.': None,
    'This is an open access article distributed under the terms of the Creative Commons Attribution License (<url>http://creativecommons.org/licenses/by/2.0</url>), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited': 'http://creativecommons.org/licenses/by/2.0',
    'This is an open-access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
    "Author's Choice —Final version full access.": None,
    'This is an open-access article distributed under the terms of the Creative Commons Attribution-Noncommercial-Share Alike 3.0 Unported License, which permits unrestricted noncommercial use, distribution, and reproduction in any medium, provided the original author and source are credited.': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution License ( http://creativecommons.org/licenses/by/2.0 ), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited': 'http://creativecommons.org/licenses/by/2.0',
    "Author's Choice - Final version full access. Creative Commons Attribution Non-Commercial License applies to Author Choice Articles": None,
    'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and Oxford University Press are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org Published by Oxford University Press on behalf of the International Epidemiological Association.': None,
    "You are free to share - to copy, distribute and transmit the work, under the following conditions: Attribution :  You must attribute the work in the manner specified by the author or licensor (but not in any way that suggests that they endorse you or your use of the work). Non-commercial :  You may not use this work for commercial purposes. No derivative works :  You may not alter, transform, or build upon this work. For any reuse or distribution, you must make clear to others the license terms of this work, which can be found at http://creativecommons.org/licenses/by-nc-nd/3.0/legalcode . Any of the above conditions can be waived if you get permission from the copyright holder. Nothing in this license impairs or restricts the author's moral rights.": None,
    'The Author(s) This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.0/uk/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution-Noncommercial License ( http://creativecommons.org/licenses/by-nc/3.0/ ), which permits unrestricted use, distribution, and reproduction in any noncommercial medium, provided the original work is properly cited.': None,
    "Author's Choice Creative Commons Attribution Non-Commercial License applies to Author Choice Articles": None,
    'The online version of this article has been published under an open access model. Users are entitled to use, reproduce, disseminate, or display the open access version of this article for non-commercial purposes provided that: the original authorship is properly and fully attributed; the Journal and the Japanese Society of Plant Physiologists are attributed as the original place of publication with the correct citation details given; if an article is subsequently reproduced or disseminated not in its entirety but only in part or as a derivative work this must be clearly indicated. For commercial re-use, please contact journals.permissions@oxfordjournals.org': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial No Derivatives License, which permits for noncommercial use, distribution, and reproduction in any digital medium, provided the original work is properly cited and is not altered in any way.': None,
    'This paper accords with the NIH Public Access policy and is governed by the licence available at http://www.rcpsych.ac.uk/pdf/NIH%20licence%20agreement.pdf': None,
    'This work is licensed under a Creative Commons Attribution NonCommercial 3.0 License (CC BYNC 3.0). Licensee PAGEPress, Italy': None,
    'This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution license http://creativecommons.org/licenses/by/3.0/.': 'http://creativecommons.org/licenses/by/3.0/',
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License ( http://creativecommons.org/licenses/by-nc/2.5 ), which permits unrestricted non-commercial use, distribution and reproduction in any medium, provided the original work is properly cited.': None,
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial License http://creativecommons.org/licenses/by-nc/2.5/ ) which permits unrestricted non-commercial use, distribution, and reproduction in any medium, provided the original work is properly cited.': None,
    'This is an open access article distributed under the Creative Commons Attribution License , which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/3.0/',
    'This is an Open Access article distributed under the terms of the Creative Commons Attribution Non-Commercial No Derivatives License, which permits for noncommercial use, distribution, and reproduction in any digital medium, provided the original work is properly cited and is not altered in any way. For details, please refer to http://creativecommons.org/licenses/by-nc-nd/3.0/': None,
    'This document may be redistributed and reused, subject to certain conditions .': None,
    'Re-use of this article is permitted in accordance with the Creative Commons Deed, Attribution 2.5, which does not permit commercial exploitation.': None,
    'This article is published under license to BioMed Central Ltd. This is an Open Access article distributed under the terms of the Creative Commons Attribution License (<ext-link ext-link-type="uri" xlink:href="http://creativecommons.org/licenses/by/2.0">http://creativecommons.org/licenses/by/2.0</ext-link>), which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited.': 'http://creativecommons.org/licenses/by/2.0'
}

copyright_statement_url_equivalents = {
    'Chiropractic & Osteopathic College of Australasia': None,
    'Copyright © 2008 by S. Karger AG, Basel': None,
    'Copyright © 2009 by S. Karger AG, Basel': None,
    'This is an open-access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original author and source are credited.': 'http://creativecommons.org/licenses/by/3.0/',
    'This is an open-access article distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use, distribution, and reproduction in any medium, provided the original work is properly cited': 'http://creativecommons.org/licenses/by/3.0/',
    'This is an open-access article, free of all copyright, and may be freely reproduced, distributed, transmitted, modified, built upon, or otherwise used by anyone for any lawful purpose. The work is made available under the Creative Commons CC0 public domain dedication.': 'http://creativecommons.org/publicdomain/zero/1.0/',
    'This is an open-access article distributed under the terms of the Creative Commons Public Domain declaration which stipulates that, once placed in the public domain, this work may be freely reproduced, distributed, transmitted, modified, built upon, or otherwise used by anyone for any lawful purpose.': 'http://creativecommons.org/publicdomain/zero/1.0/',
    'This is an open-access article distributed under the terms of the Creative Commons Public Domain declaration, which stipulates that, once placed in the public domain, this work may be freely reproduced, distributed, transmitted, modified, built upon, or otherwise used by anyone for any lawful purpose.': 'http://creativecommons.org/publicdomain/zero/1.0/',
    "This is an Open Access article: verbatim copying and redistribution of this article are permitted in all media for any purpose, provided this notice is preserved along with the article's original URL.": None,
    '© Biomedical Engineering Society 2010': None,
    '© Springer Science+Business Media, Inc. 2007': None,
    '© Springer Science+Business Media, LLC 2007': None,
    '© Springer Science+Business Media, LLC 2008': None,
    '© Springer Science+Business Media, LLC 2009': None,
    '© Springer Science+Business Media, LLC 2010': None,
    '© Springer Science+Business Media, LLC 2011': None,
    '© Springer Science+Business Media, LLC and the Cardiovascular and Interventional Radiological Society of Europe (CIRSE) 2009': None,
    '© Springer Science+Business Media, LLC and the Cardiovascular and Interventional Radiological Society of Europe (CIRSE) 2010': None,
    '© Springer Science+Business Media B.V. 2006': None,
    '© Springer Science+Business media B.V. 2006': None,
    '© Springer Science+Business Media B.V. 2007': None,
    '© Springer Science + Business Media B.V. 2007': None,
    '© Springer Science+Business Media B.V. 2008': None,
    '© Springer Science+Business Media B.V. 2009': None,
    '© Springer Science+Business Media B.V. 2010': None,
    '© Springer Science+Business Media B.V. 2011': None,
    '© Springer-Verlag 2007': None,
    '© Springer-Verlag 2008': None,
    '© Springer-Verlag 2009': None,
    '© Springer-Verlag 2010': None,
    'Copyright © 2011 Macmillan Publishers Limited': None,
    'Copyright © 2012 Macmillan Publishers Limited': None,
    '© 2007 The Authors Journal compilation © 2007 Blackwell Publishing Ltd': None,
    '© 2008 Dove Medical Press Limited. All rights reserved': None,
    '© The Author(s) 2007': None,
    '© The Author(s) 2008': None,
    '© The Author(s) 2009': None,
    '© The Author(s) 2010': None,
    '© The Author(s) 2011': None,
    '© The Author(s) 2012': None,
}

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
    Given an ElementTree, returns article license URL.
    """
    license_text = None
    license_url = None
    copyright_statement_text = None

    license = tree.find('front//*license')
    copyright_statement = tree.find('front//*copyright-statement')

    def _get_text_from_element(element):
        text = ' '.join(element.itertext()).encode('utf-8')  # clean encoding
        text = ' '.join(text.split())  # clean whitespace
        return text

    if license is not None:
        try:
            license_url = license.attrib['{http://www.w3.org/1999/xlink}href']
        except KeyError: # license URL is possibly in in <ext-link> element
            try:
                ext_link = license.find('license-p/ext-link')
                if ext_link is not None:
                    license_url = \
                        ext_link.attrib['{http://www.w3.org/1999/xlink}href']
            except KeyError: # license statement is in plain text
                license_text = _get_text_from_element(license)
    elif copyright_statement is not None:
        copyright_statement_text = _get_text_from_element(copyright_statement)
    else:
        #logging.error('No <license> or <copyright-statement> element found in XML.')
        return None, None, None

    if license_url is None:
        if license_text is not None:
           try:
               license_url = license_url_equivalents[license_text]
           except:
             #logging.error('Unknown license: %s', license_text)
             pass

        elif copyright_statement_text is not None:
            copyright_statement_found = False
            for text in copyright_statement_url_equivalents.keys():
                if copyright_statement_text.endswith(text):
                    license_url = copyright_statement_url_equivalents[text]
                    copyright_statement_found = True
                    break
            if not copyright_statement_found:
                #logging.error('Unknown copyright statement: %s', copyright_statement_text)
                pass

    def _fix_license_url(license_url):
        if license_url in license_url_fixes.keys():
            return license_url_fixes[license_url]
        return license_url

    if license_text is not None:
        license_text = license_text.decode('utf-8')

    if copyright_statement_text is not None:
        copyright_statement_text = copyright_statement_text.decode('utf-8')

    if license_url is not None:
        return _fix_license_url(license_url), license_text, copyright_statement_text
    else:
        return None, license_text, copyright_statement_text

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
        except KeyError:
            result['mimetype'] = ''
            result['mime-subtype'] = ''
        result['url'] = _get_supplementary_material_url(
            _get_pmcid(tree),
            media.attrib['{http://www.w3.org/1999/xlink}href']
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
