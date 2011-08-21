#! /usr/bin/env/python
'''
plugin.py

nose plugin to run tests in an extension library

Uses the _testext extension to load and run the test, via the runner helper
'''

import logging 
import os
from nose.plugins.base import Plugin
from nose.util import tolist
import re 
from datetime import datetime
log = logging.getLogger('nose.plugins')

class TestInfo(object): 
	def __init__(self):
		self.test_id = None
		self.covers = None 
		self.summary = None
		self.preconditions = None
		self.datasets = None
		self.rationale = None
		self.steps = [] 
		self.passed = None

class TestExt(Plugin):
	name = 'testext'

	def options(self, parser, env=os.environ):
		parser.add_option(
			'--with-testext', action='store_true', dest='testext_enabled',
 			default=env.get('NOSE_TESTEXT'),
			help='Enable test discovery and execution in C extensions [NOSE_TESTEXT]'
		)
		parser.add_option(
			'--testext-regex', action='store', dest='testext_regex',
 			default=env.get('NOSE_TESTEXT_REGEX'),
			help='Regular expression to match test functions [NOSE_TESTEXT_REGEX]'
		)

	def configure(self, options, conf):
		if not self.can_configure:
			return
		self.enabled = options.gendocs_enabled
		self.regex = options.gendocs_output or "testext_test"
		self.conf = conf

