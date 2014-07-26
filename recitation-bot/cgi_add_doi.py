import cgi
import cgitb

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
print "<input type='submit' value='submit form' />"
print "</form>"
form = cgi.FieldStorage()
#print form
print "<h2>I will try and upload:</h2>"
print "<ul>"
for field_name in form:
    field=form[field_name]
    if field.name == 'doi':
        print "<li>"
        print field.name
        print " = "
        doi = cgi.escape(repr(field.value))
        doi_plain = field.value
        print doi
        print "</li>"
        if form['doi'].value:
            dequeue = open('/data/project/recitation-bot/recitation-bot/jump_the_queue.log','a')
            dequeue.write(doi_plain+'\n')
            dequeue.close()

print "</ul>"


print "</body>"
print "</html>"
