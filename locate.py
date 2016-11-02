#!/usr/bin/env python

import os

labs_home = '/data/project/recitation-bot/'
if os.path.exists(labs_home):
	running_on_labs = True
	os.chdir(os.path.join(labs_home, 'new-bot'))
else:
	running_on_labs = False

def locate(path, project = False):
	"""bases to the project directory if project is true, else home"""
	base = os.path.join(labs_home, 'new-bot') if project else labs_home
	return os.path.join(base if running_on_labs else '.', path)
