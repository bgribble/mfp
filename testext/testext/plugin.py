#! /usr/bin/env/python
'''
plugin.py

nose plugin to run tests in an extension library

Uses the _testext extension to load and run the test, via the runner helper
'''

import logging 
import sys, os
from nose.plugins.base import Plugin
from nose.util import tolist
import re 
from datetime import datetime
from unittest import TestCase


log = logging.getLogger('nose.plugins')

class NullTestCase (TestCase):
	def __init__(self, libname):
		TestCase.__init__(self)
		self._testMethodDoc = libname + ' (null test)'

	def runTest(self):
		return True

class DynLibTestCase (TestCase):
	def __init__(self, libname, funcname, setup, teardown):
		self.funcname = funcname
		self.libname = libname
		self.setupname = setup
		self.teardownname = teardown
		self.expected = 0
		if funcname.endswith("expect_fail"):
			self.expected = 1
		elif funcname.endswith("expect_err"):
			self.expected = 2

		TestCase.__init__(self)
		self._testMethodDoc = '%s:%s' % (libname.split('/')[-1], funcname)

	def runTest(self):
		import subprocess
		p = subprocess.Popen(["testext_wrapper", self.libname, self.funcname, 
					          self.setupname or 'None', self.teardownname or 'None'],
					         stdout=subprocess.PIPE)
		stdout, stderr = p.communicate()
		p.wait()
		
		print stdout
		if stderr is not None:
			print "---- stderr start ----"
			print stderr
			print "---- stderr end ----"
		if p.returncode > 2:
			p.returncode = 2

		if p.returncode == self.expected:
			return True
		elif (p.returncode == 1 or self.expected == 2
		      or (p.returncode == 0 and self.expected == 1)):
			raise AssertionError()
		else:
			raise Exception()

class TestExt(Plugin):
	name = 'testext'
	regex = None 
	fileinfo = {}

	def options(self, parser, env=os.environ):
		parser.add_option(
			'--with-testext', action='store_true', dest='testext_enabled',
 			default=env.get('NOSE_TESTEXT'),
			help='Enable test discovery and execution in C extensions [NOSE_TESTEXT]'
		)
		parser.add_option(
			'--testext-regex', action='store', dest='testext_regex',
 			default=env.get('NOSE_TESTEXT_REGEX', "^test_.*"),
			help='Regular expression to match test functions [NOSE_TESTEXT_REGEX]'
		)

	def configure(self, options, conf):
		if not self.can_configure:
			return
		self.enabled = options.testext_enabled
		self.regex = options.testext_regex
		self.conf = conf

	def wantFile(self, filename):
		'''wantFile: we want all dynamic libraries (*.so.x.y.z)'''
		libre = r".*\.so(\.[0-9]+)*$"
		if re.match(libre, filename):
			info = self.find_fileinfo(filename)
			if info:
				self.fileinfo[filename] = info
				return True
		return False

	def wantDirectory(self, dirname):
		'''wantDirectory: we want all directories'''
		return True

	def find_fileinfo(self, filename):
		import subprocess
		p = subprocess.Popen(['readelf', '-W', '-s', filename], stdout=subprocess.PIPE)
		syms, stderr = p.communicate()
	
		testnames = {}
		setup = None
		teardown = None
	
		for s in syms.split('\n'):
			m = re.search(r'FUNC .* ([^ ]+)$', s)
			if m:
				if re.match(self.regex, m.group(1)):
					tname = m.group(1)
					if tname.endswith("SETUP"):
						setup = tname
					elif tname.endswith("TEARDOWN"):
						teardown = tname
					elif not tname.endswith("skip"):
						testnames[tname] = True
		tt = testnames.keys()
		tt.sort()
		if len(tt) > 0:
			return { 'tests': tt, 'setup': setup, 'teardown': teardown }
			
	def loadTestsFromFile(self, filename):
		info = self.fileinfo.get(filename)
		if info:
			setup = info['setup']
			teardown = info['teardown']

			for s in info['tests']:
				yield DynLibTestCase(filename, s, setup, teardown)


