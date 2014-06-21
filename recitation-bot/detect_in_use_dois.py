sql enwiki
select page_title, el_to from externallinks left join page on page_id = el_from where page_namespace = 0 and el_index like 'http://org.doi.dx%';

import MySQLdb.connect(host='enwiki.labsdb', db='enwiki_p', port=3306, read_default_file='~/replica.my.cnf')
cursor = conn.cursor()

    qstring = u'''SELECT rev_timestamp FROM enwiki_p.revision_\
userindex WHERE rev_user_text like "'''+ user + u'''";'''
    uqstring = qstring.encode('utf-8')
    cursor.execute(uqstring)
    results = cursor.fetchall()
