#!/usr/bin/python2.5
# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

import settings
import repscanner

# import the django environment first before using any local modules
from django.core.management import setup_environ
setup_environ(settings)
from webreview.models import Repository

if __name__ == '__main__':
   for r in Repository.objects.all():
      print "Scanning %s" % r.name
      c = repscanner.RepositoryScanner(r)
      c.run()


