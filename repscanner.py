#!/usr/bin/python2.5
# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

import os
import settings
import unittest
import vclib.ccvs

from datetime import datetime

# import the django environment first before using any local modules
from django.core.management import setup_environ
setup_environ(settings)
from webreview.models import Repository, File, Change, User

class Bug: pass

def prevRev(rev):
   assert(len(rev) % 2 == 0)
   assert(len(rev) >= 2)
   last = rev[-1:][0]
   newrev = None
   if last > 1:
      newrev = rev[:-1] + (last-1,)
   else:
      if len(rev) > 2:
         newrev = rev[:-2]
   if newrev:
      return ".".join([str(c) for c in newrev])
   else:
      return "New"

class RevisionList:
   def __init__(self, repo, file):
      try:
         self.revs = repo.itemlog([file], None, {})
      except vclib.ItemNotFound:
         self.revs = []

   def getlatestrev(self):
      if len(self.revs) == 0:
         return None
      latest = self.revs[0]
      for rev in self.revs:
         if rev.date > latest.date:
            latest = rev
      return latest

   def getrevssince(self, xrev):
      if xrev:
         zrev = self.revbystr(xrev)
      revssince = []
      for rev in self.revs:
         if xrev == None or rev.date > zrev.date:
            revssince.append(rev)
      return revssince

   def revbystr(self, revstr):
      for rev in self.revs:
         if rev.string == revstr:
            return rev
      return None

class RepositoryScanner:
   def __init__(self, repository):
      self.r = repository
      self.repo = vclib.ccvs.CCVSRepository("foo", self.r.path)

   def run(self):
      for filename in self.getFilenameList():
         self.handleFile(filename)

   def getbranchname(self, file, rev):
      revs = self.repo.itemlog([file], rev, {})
      for r in revs:
         blist = [b for b in r.branches if b.is_branch == True and b.number]
      return blist[0].name

   def getFilenameList(self, dir="."):
      ret = []
      for entry in self.repo.listdir([dir], None, {}):
         if entry.kind == 'FILE':
            ret.append(os.path.join(dir, entry.name))
         elif entry.kind == 'DIR':
            ret += self.getFilenameList(os.path.join(dir, entry.name))
      return ret

   def checkUser(self, username):
      qs = User.objects.filter(name=username)
      if len(qs) == 0:
         user = User() 
         user.name = username
         user.save()
         return user
      else:
         return qs[0]

   def handleFile(self, filename):
      # check if a record for this file exists already 
      attic = False
      full_path = os.path.join(self.r.path, "%s,v" % filename)
      try:
         statinfo = os.stat(full_path)
      except OSError:
         try:
            full_path = os.path.join(
                           os.path.dirname(full_path),
                           'Attic',
                           os.path.basename(full_path))
            statinfo = os.stat(full_path)
            attic = True
         except OSError:
            print "Cannot find file %s" % full_path
            return
      if attic:
         cvspath = os.path.join(
                        os.path.dirname(filename), 'Attic',
                        os.path.basename(filename))
      else:
         cvspath = filename
      file = None
      qs = File.objects.filter(repository=self.r).filter(name=filename)
      if len(qs) == 0:
         # add new file and leave, there cannot be a change on a new file
         revlist = RevisionList(self.repo, cvspath)
         rev = revlist.getlatestrev()
         if rev:
            print "Adding %s r%s" % (filename, rev.string)
            file = File()
            file.repository = self.r
            file.name = filename
            file.last_change = datetime.fromtimestamp(0)
            file.last_rev = None
            file.save()
         else:
            print "%s" % cvspath
            raise Bug
      elif len(qs) == 1:
         file = qs[0]
      else:
         raise Bug

      # check timestamp
      if datetime.fromtimestamp(statinfo.st_mtime) == file.last_change:
         # timestamps match, no change since last scan
         return

      # check revision
      revlist = RevisionList(self.repo, cvspath)
      rev = revlist.getlatestrev()
      if rev and rev.string == file.last_rev:
         print "%s: %s/%s" % (file.name, rev.string, file.last_rev)
         # when timestamp changed but not revision, update
         # timestamp in order not to check again
         file.last_change = datetime.fromtimestamp(statinfo.st_mtime)
         file.save()
         return

      # add all changes since last revision
      for rev in revlist.getrevssince(file.last_rev):
         print "Adding change %s %s (%s)" % (filename, rev.string, file.last_rev)
         c = Change()
         c.file = file
         c.user = self.checkUser(rev.author)
         c.commit_time = datetime.fromtimestamp(rev.date)
         c.rev_old = prevRev(rev.number)
         c.rev_new = rev.string
         c.logmessage = unicode(rev.log, "iso-8859-1").encode("utf-8")
         if rev.changed:
            c.diffstat = rev.changed
         else:
            c.diffstat = 'new'
         c.save()

      # update timestamp
      print "Updating %s" % filename
      file.last_change = datetime.fromtimestamp(statinfo.st_mtime)
      file.last_rev = revlist.getlatestrev().string
      file.save()

class PrevRevTest(unittest.TestCase):
   def testRevs(self):
      self.assert_(prevRev((1,1)) == "New")
      self.assert_(prevRev((1,2)) == "1.1")
      self.assert_(prevRev((1,3)) == "1.2")
      self.assert_(prevRev((1,1000)) == "1.999")
      self.assert_(prevRev((1,1,1,1)) == "1.1")
      self.assert_(prevRev((1,1,1,2)) == "1.1.1.1")
      self.assert_(prevRev((1,1,2,99)) == "1.1.2.98")
      self.assert_(prevRev((1,1,1,1,1,1)) == "1.1.1.1")
      self.assert_(prevRev((1,1,1,1,1,2)) == "1.1.1.1.1.1")

if __name__ == '__main__':
   unittest.main()


#diff = r.rawdiff(["xx.c"], "1.55", ["xx.c"], "1.56", 1)
#print diff.read(10000)


