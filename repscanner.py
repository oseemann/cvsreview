#!/usr/bin/python2.5
# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

import os
import settings
import unittest
from datetime import datetime

# import the django environment first before using any local modules
from django.core.management import setup_environ
setup_environ(settings)

from webreview.models import Repository, File, Change, User
from repository import RepositoryAccess, RevisionList, previousRev

import vclib.ccvs

class Bug(Exception):
   pass

class RepositoryScanner:
   def __init__(self, repository):
      self.r = repository
      self.repo = RepositoryAccess(repository.path)

   def run(self):
      for filename in self.repo.getFilenameList():
         self.handleFile(filename)

   def checkUser(self, username):
      """ Return matching user record, create new one if non-existant """
      qs = User.objects.filter(name=username)
      if len(qs) == 0:
         user = User() 
         user.name = username
         user.save()
         return user
      else:
         return qs[0]

   def addFile(self, filename):
      file = File()
      file.repository = self.r
      file.name = filename
      file.last_change = datetime.fromtimestamp(0)
      file.last_rev = None
      file.save()
      print "Added %s" % (filename)
      return file

   def addChange(self, file, rev):
      print "Adding change %s %s" % (file.name, rev.string)
      c = Change()
      c.file = file
      c.user = self.checkUser(rev.author)
      c.commit_time = datetime.fromtimestamp(rev.date)
      c.rev_old = previousRev(rev.number)
      c.rev_new = rev.string
      c.logmessage = unicode(rev.log, "iso-8859-1").encode("utf-8")
      c.diffstat = rev.changed or 'new'
      c.save()

   def checkFile(self, filename):
      qs = File.objects.filter(repository=self.r).filter(name=filename)
      if len(qs) == 1:
         return qs[0]
      elif len(qs) == 0:
         return None 
      else:
         raise Bug()

   def handleFile(self, filename):
      file = self.checkFile(filename)
      if file == None:
         file = self.addFile(filename)

      # if timestamps match: no change since last scan, skip
      timestamp = self.repo.getTimestamp(filename)
      if timestamp == file.last_change:
         return

      # if revision has not changed, update timestamp and continue
      revlist = RevisionList(self.repo, filename)
      rev = revlist.getNewest()
      if rev.string == file.last_rev:
         print "%s: %s/%s" % (file.name, rev.string, file.last_rev)
         file.last_change = timestamp
         file.save()
         return

      # add all changes since last known revision
      for rev in revlist.getSince(file.last_rev):
         self.addChange(file, rev)

      # update timestamp and revision
      file.last_change = timestamp
      file.last_rev = revlist.getNewest().string
      file.save()

