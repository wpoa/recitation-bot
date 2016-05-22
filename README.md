recitation-bot
==============

Pronounced as in "recitation" (reh-sih-tay-shun) or "re-citation" (ree-sigh-tay-shun).

To create clear signals of "open access"ness in Wikipedia references, when triggered, this MediaWiki
bot uploads permissible cited content to relevant Wikimedia projects and updates corresponding
citations on Wikipedia. Intended to replace citation-bot, with a focus on DOIs and Open Access
scholarly literature.

Read more at tha [Signalling
OA-ness](https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Open_Access/Signalling_OA-ness) page
under [WikiProject Open Access](https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Open_Access) on
the [English language Wikipedia](https://en.wikipedia.org/).


Entry points
------------

+ `task_supervisior.py` is the main thread which runs a dequeue being fed by 'producers' and eaten by 'consumers'
+ `journal_article.py` is the consumer that deals with converting and uploading articles
+ `detect_in_use_dois.py` is a producer that queries the sql replicas to find new dois to append to the end of the dequeue
+ `jump_the_queue.py` is a producer that is a webserver that takes immediate requests that go on the front of the dequeue

To Launch
---------
+ login in to wikimedia tools labs
+ `become recitation-bot`
+ run `sh submit_bot_to_grid.sh`

# Troubleshooting
---------------
## EOFError on commons.login()
--------
delete the cookie pywikibot.lwp in the ~/.pywikibot folder. then run something like
source env/bin/activate
import pywikibot
commons = pywikibot.Site('commons','commons')
commons.login()
enws = pywikibot.Site('en','wikisource')
enws.login()

and you should get a new cookie that will work.
you might have gotten logged out for a number of reasons including the bot being blocked.

License
-------

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>
