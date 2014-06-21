import MySQLdb
import datetime
import shelve


class doi_finder():
    def __init__(self):
        #@TODO make this languag agnostic
        self.conn = MySQLdb.connect(host='enwiki.labsdb', db='enwiki_p', port=3306, read_default_file='~/replica.my.cnf')
        self.cursor = self.conn.cursor()
        
        self.qstring = u'''select page_title, el_to from externallinks left join page on page_id = el_from where page_namespace = 0 and el_index like 'http://org.doi.dx%';'''
        self.uqstring = self.qstring.encode('utf-8')
        #shelf is keyed by doi, and values is a list of pages they appear on
        self.shelf = shelve.open('doi_detector_shelf', writeback=False)


    def get_doi_list(self, time=None):
        new_additions = list()
        self.cursor.execute(self.uqstring)
        return self.cursor.fetchall()

    def find_new_doi_article_pairs(self):
        curr = self.get_doi_list()
        new_additions = list()
        for title, doi_str in curr:
            print title, doi_str
            doi = doi_str.split('http://org.doi.dx/')
            if doi not in self.shelf.keys():
                new_additions.append((doi, title) )
            else:
                title_list = self.shelf[doi]
                if title not in title_list:
                    title_list.append(title)
                    self.shelf[doi] = title_list
                    new_additions.append( (doi, title) )
        
        print('this many new additions',len(new_additions))
                
    
    def run_in_loop(self):
        while True:
            print(str(datetime.datetime.now()))
            self.find_new_doi_article_pairs()



if __name__ == '__main__':
    getter = doi_finder()
    getter.run_in_loop()
