from jinja2 import Environment, FileSystemLoader
import os
import datetime

env = Environment(loader=FileSystemLoader('/data/project/recitation-bot/recitation-bot/templates/'))

status_template = env.get_template('status_page.html')

def make_status_page(doi, success, error_msg, ja, inqueue):
    success_str = 'succeeded' if success else 'failed'
    if success is None:
        success_str = 'waiting'
    time = datetime.datetime.utcnow()
    try:
        metadata = ja.metadata
    except:
        metadata = dict() #empty dict to avoid errors
    try:
        doiurl = ja.doiurl()
    except:
        doiurl = None #we actually check for this being empty
    output = status_template.render(doi=doi, success_str=success_str,
    error_msg=error_msg, metadata=metadata, doiurl=doiurl, time=time,
    inqueue=inqueue)

    page_base_path = '/data/project/recitation-bot/public_html/'
    doi_split = doi.rsplit('/', 1) # split on last '/', always at least 1
    page_sub_path = doi_split[0]
    page_file_name = doi_split[1]
    page_dir_path = page_base_path + page_sub_path + "/"
    page_full_path = page_dir_path + page_file_name + '.html'

    old_page_content = ''
    if os.path.isfile(page_full_path):
        old_page_content = open(page_full_path, 'r').read()
    elif not os.path.exists(page_dir_path):
        os.makedirs(page_dir_path)
    appended_output = output + old_page_content.decode('utf-8')
    page = open(page_full_path, 'w')
    uni_out = appended_output.encode('utf-8')
    page.write(uni_out)
    page.close()


#test
if __name__ == '__main__':
    make_status_page(doi='123', success=False, error_msg='error here', ja=None, inqueue=False)
