Start on tools-labs using the webservice command as follows:

webservice --backend=kubernetes python start

(See https://wikitech.wikimedia.org/wiki/Help:Tool_Labs/Web)

On your machine:

to get dependencies set up:
- install libxml2 and libxml2-dev such that xsltproc is on your path
- (within a virtualenv if you want) pip -r requirements.txt install
- set up authentication for pywikibot

to start:
- python3 proto-webservice.py

go to port 8080 on the machine you are running on to use the service
