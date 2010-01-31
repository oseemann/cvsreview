#!/usr/bin/python2.5
# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),'..')))

import app.settings

# import the django environment first before using any local modules
from django.core.management import setup_environ
setup_environ(app.settings)
from app.webreview.models import Repository
from app.scanner.repscanner import RepositoryScanner

if __name__ == '__main__':
   for r in Repository.objects.all():
      print "Scanning %s" % r.name
      RepositoryScanner(r).run()


