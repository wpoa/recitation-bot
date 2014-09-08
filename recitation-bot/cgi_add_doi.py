import cgi
import cgitb
import os

cgitb.enable()

print "Content-Type: text/html"     # HTML is following
print                               # blank line, end of headers
print "<title>jump a doi to the front of the queue</title>"
#print "who dares enter a doi"
print "<html>"
print "<body>"

# standard single line text field
print "<h1>jump a doi to the front of the queue</h1>"
print "<form method='post'>"
print "Enter a doi (don't include 'http://dx.doi.org/'):"
print "<input type='text' name='doi' value='' />"
print "<input type='checkbox' name='reupload' />"
print "<input type='submit' value='submit form' />"
print "</form>"
form = cgi.FieldStorage()
#print form
for field_name in form:
    field=form[field_name]
    if field.name == 'doi':
        doi_plain = field.value
        doi_safe = cgi.escape(repr(doi_plain))
        print "<p>%s will be uploaded shortly</p>" % doi_safe
        url = 'http://tools.wmflabs.org/recitation-bot/' + doi_plain + '.html'
        print "<p>Follow the upload status at <a href='%s'>%s</a> </p>" % (url, url)
        if form['doi'].value:
            dequeue = open('/data/project/recitation-bot/recitation-bot/jump_the_queue.log','a')
            dequeue.write(doi_plain+'\n')
            dequeue.close()

        waiting_page_path = '/data/project/recitation-bot/public_html/'+doi_plain+'.html'
        if not os.path.exists(os.path.dirname(waiting_page_path)):
            os.makedirs(os.path.dirname(waiting_page_path))
        if os.path.isfile(waiting_page_path):
            pass #there's nothing to do since its already been uplaoded
        else:
            waiting_page = open(waiting_page_path, 'w')
            waiting_text = r'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<title>waiting</title>
<html>
<body>
<p>%s being processed, we have to fetch and crunch a lot of data, long articles can take upto 5 minutes depending on traffic loads</p>
</body>
</html>''' % doi_plain
            waiting_page.write(waiting_text)
            waiting_page.close()


print "</ul>"
print "</body>"
print "</html>"
