recitation-bot
==============

To create clear signals of "open access"ness in Wikipedia references, when triggered, this MediaWiki bot uploads permissible cited content to relevant Wikimedia projects and updates corresponding citations on Wikipedia. Intended to replace citation-bot, with a focus on DOIs and Open Access scholarly literature.

Entry points
============
+ `task_supervisior.py` is the main thread which runs a dequeue being fed by 'producers' and eaten by 'consumers'
+ `journal_article.py` is the consumer that deals with converting and uploading articles
+ `detect_in_use_dois.py` is a producer that queries the sql replicas to find new dois to append to the end of the dequeue
+ `jump_the_queue.py` is a producer that is a webserver that takes immediate requests that go on the front of the dequeue