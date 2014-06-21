#!/usr/bin/env python
# -*- coding: utf-8 -*-

def make_datestring(year, month, day):
    datestring = "%04d" % year  # YYYY
    if month is not None:
        datestring += "-%02d" % month  # YYYY-MM
    if day is not None:
        datestring += "-%02d" % day  # YYYY-MM-DD
    return datestring


def _escape(text):
    for original, replacement in [
        ('=', '{{=}}'),
        ('|', '{{!}}')
    ]:
        try:
            text = text.replace(original, replacement)
        except AttributeError:
            pass
    return text

def _trim(text):
    return ' '.join(text.split())

def page(metadata, caption):
    
    article_doi = metadata['doi']
    authors = metadata['article-contrib-authors']
    article_title = metadata['article-title'] 
    # = metadata['article-abstract']
    journal_title = metadata['journal-title']
    article_year = metadata['article-year']
    article_month = metadata['article-month']
    article_day = metadata['article-day']
    article_url = metadata['article-url']
    license_url = metadata['article-license-url']
    # = metadata['article-license-text']
    # = metadata['article-copyright-statement']
    # = metadata['article-copyright-holder']
    categories = metadata['article-categories']

    mimetype = 'image' #need this for templating
    
    
    license_templates = {
        u'http://creativecommons.org/licenses/by/2.0/': '{{cc-by-2.0}}',
        u'http://creativecommons.org/licenses/by-sa/2.0/': '{{cc-by-sa-2.0}}',
        u'http://creativecommons.org/licenses/by/2.5/': '{{cc-by-2.5}}',
        u'http://creativecommons.org/licenses/by-sa/2.5/': '{{cc-by-sa-2.5}}',
        u'http://creativecommons.org/licenses/by/3.0/': '{{cc-by-3.0}}',
        u'http://creativecommons.org/licenses/by-sa/3.0/': '{{cc-by-sa-3.0}}',
        u'http://creativecommons.org/licenses/by/4.0/': '{{cc-by-4.0}}',
        u'http://creativecommons.org/licenses/by-sa/4.0/': '{{cc-by-sa-4.0}}'
    }
    
    if license_url:
        license_template = license_templates[license_url]
    else:
        license_template = ''

    text = "=={{int:filedesc}}==\n\n"
    text += "{{Information\n"
    
    if caption:
        description = _escape(caption)
    else:
        description = "%s %s" % (_escape('Media belonging article cited on Wikipedia with DOI:'), _escape(article_doi))
    
    text += "|Description=\n"
    if len(description.strip()) > 0:
        text+= "{{en|1=%s}}\n" % description
    text += "|Date= %s\n" % make_datestring(article_year, article_month, article_day)
    

    label = ("%s file" % mimetype).capitalize()
    text += "|Source= [%s %s] from " % (article_url, _escape(label))
    text += "{{Cite journal\n"
    text += "| author = %s\n" % _escape(authors)
    text += "| title = %s\n" % _escape(_trim(article_title))
    text += "| doi = %s\n" % _escape(article_doi)
    text += "| journal = %s\n" % _escape(journal_title)
    text += "| year = %s\n" % _escape(article_year)
    text += "}}\n"
    text += "|Author= %s\n" % _escape(authors)
    text += "|Permission= %s\n" % license_template
    text += "|Other_fields={{Information field|name=Provenance|value= {{Open Access Media Importer}} }}\n"
    text += "}}\n\n"

    def _capitalize_properly(word):
        if len(word) == 1: # single letters should pass through unchanged
            return word
        if word[1:] == word[1:].lower():  # word has no capital letters inside
            return word.lower()
        else:  # words like 'DNA' or 'HeLa' should not be touched
            return word

    def _postprocess_category(category):
        if '(' in category:
            category = category.split('(')[0]
        if ',' in category:
            category_parts = category.split(',')
            category_parts.reverse()
            category = ' '.join(category_parts)
        processed_category = []
        for word in category.strip().split(' '):
            wordparts = []
            for part in word.split('-'):
                wordparts.append(_capitalize_properly(part))
            processed_category.append('-'.join(wordparts))
        category = ' '.join(processed_category)
        return category[0].capitalize() + category[1:]

    for category in categories:
        category = _postprocess_category(category)
        if len(category.split()) > 1:  # no single-word categories
            text += "[[Category:%s]]\n" % _escape(category)
    text += "[[Category:Media from %s]]\n" % _escape(journal_title)
    text += "[[Category:Uploaded with reCitation Bot]]\n"
    text += '[[Category:Uploaded_with reCitation Bot and needing category review]]\n'
    return text
