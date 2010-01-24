#!/usr/bin/python
# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

import os
from datetime import datetime
import unittest
import vclib.ccvs


class UnknownRevision(Exception):
   """ Exception raised when a requested revision does not exist
       in a given file. """
   pass

class UnknownFile(Exception):
   """ Exception raised when a requested file does not exist
       in a given repository """
   pass

def previousRev(rev):
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
   """ Represents a list of all revisions of a given file in a repository. """
   def __init__(self, repo, file):
      self.cur = 0
      try:
         self.revs = repo.itemlog([file], None, {})
      except vclib.ItemNotFound:
         raise UnknownFile()

   def next(self):
      if self.cur >= len(self.revs):
         self.cur = 0
         raise StopIteration
      self.cur += 1
      return self.revs[self.cur-1]

   def __iter__(self):
      return self

   def all(self):
      """ Returns a list of all revisions.
          The order is arbitrary. """
      return self.revs

   def getNewest(self):
      """ Returns the revision with the highest timestamp. """
      if len(self.revs) == 0:
         return None
      newest = self.revs[0]
      for rev in self.revs:
         if rev.date > newest.date:
            newest = rev
      return newest

   def getSince(self, revstr=None):
      """ Returns a list of revisions with a higher timestamp than
          the given revision. If None is given, all are returned. """
      if revstr == None:
         return self.all()
      try:
         zrev = [r for r in self.revs if r.string == revstr][0]
      except IndexError:
         raise UnknownRevision()
      return [rev for rev in self.revs if rev.date > zrev.date]

class RepositoryAccess(object):
   def __init__(self, path):
      self.path = path
      self.repo = vclib.ccvs.CCVSRepository("foo", self.path)

   def getFilenameList(self, dir="."):
      """ Returns a list of all files in the repository.
          Recursively includes files of all subdirectories.
          Excludes CVSROOT. """
      ret = []
      for entry in self.repo.listdir([dir], None, {}):
         if entry.name == 'CVSROOT':
            pass
         elif entry.kind == 'FILE':
            ret.append(os.path.join(dir, entry.name))
         elif entry.kind == 'DIR':
            ret += self.getFilenameList(os.path.join(dir, entry.name))
         else:
            pass
      return ret

   def getRevisions(self, filename):
      return RevisionList(self.repo, filename)

   def getTimestamp(self, filename):
      statinfo = os.stat(self._fullpath(filename))
      return datetime.fromtimestamp(statinfo.st_mtime)

   def _fullpath(self, filename):
      """ Returns the absolute path of a given filename.
          Takes into account deleted files that remain in the 'Attic'."""
      attic = False
      full_path = os.path.join(self.path, "%s,v" % filename)
      (dir, file) = os.path.split(full_path)
      try:
         statinfo = os.stat(full_path)
      except OSError:
         try:
            full_path = os.path.join(dir, 'Attic', file)
            statinfo = os.stat(full_path)
            attic = True
         except OSError:
            raise UnknownFile()
      return full_path

class RepositoryTest(unittest.TestCase):
   def testFileList(self):
      r = RepositoryAccess('test/repo')
      files = r.getFilenameList()
      #for f in files: print f
      self.assert_('./module1/file1.txt' in files)
      self.assert_('./module1/file2.txt' in files)
      self.assert_('./module1/file3.txt' in files)
      self.assert_('./module2/gpl.txt' in files)
      self.assert_('./module2/deleted_file.txt' in files)
      self.assert_('./module2/timestamp.txt' in files)
      self.assert_('./module2/timestamp_deleted.txt' in files)
      self.assert_(len(files) == 7)

   def testAllRevisions(self):
      r = RepositoryAccess('test/repo')
      revisions = r.getRevisions('./module1/file2.txt')
      allrevs = [r.string for r in revisions]
      self.assert_('1.1.1.1' in allrevs)
      self.assert_('1.1' in allrevs)
      self.assert_('1.2' in allrevs)
      self.assert_('1.3' in allrevs)
      self.assert_(len(allrevs) == 4)

   def testGetNewest(self):
      r = RepositoryAccess('test/repo')
      revisions = r.getRevisions('./module1/file2.txt')
      self.assert_('1.3' == revisions.getNewest().string)
      revisions = r.getRevisions('./module1/file1.txt')
      self.assert_('1.1' == revisions.getNewest().string)

   def testGetSince(self):
      r = RepositoryAccess('test/repo')
      revisions = r.getRevisions('./module1/file2.txt')

      self.assertRaises(UnknownRevision, revisions.getSince, '1.4')

      revs = [r.string for r in revisions.getSince('1.3')]
      self.assert_(len(revs) == 0)

      revs = [r.string for r in revisions.getSince('1.2')]
      self.assert_('1.3' in revs)
      self.assert_(len(revs) == 1)

      revs = [r.string for r in revisions.getSince('1.1')]
      self.assert_('1.2' in revs)
      self.assert_('1.3' in revs)
      self.assert_(len(revs) == 2)

      revs = [r.string for r in revisions.getSince()]
      self.assert_('1.1.1.1' in revs)
      self.assert_('1.1' in revs)
      self.assert_('1.2' in revs)
      self.assert_('1.3' in revs)
      self.assert_(len(revs) == 4)

      self.assertRaises(UnknownRevision, revisions.getSince, '1.0')

   def testTimestamp(self):
      r = RepositoryAccess('test/repo')
      ts = r.getTimestamp('./module2/timestamp.txt')
      self.assert_(ts == datetime(2010, 1, 24, 14, 20, 12, 431180))

   def testTimestampDeleted(self):
      r = RepositoryAccess('test/repo')
      ts = r.getTimestamp('./module2/timestamp_deleted.txt')
      self.assert_(ts == datetime(2010, 1, 24, 14, 58, 59, 382430))

class PreviousRevTest(unittest.TestCase):
   def testRevs(self):
      self.assert_(previousRev((1,1)) == "New")
      self.assert_(previousRev((1,2)) == "1.1")
      self.assert_(previousRev((1,3)) == "1.2")
      self.assert_(previousRev((1,1000)) == "1.999")
      self.assert_(previousRev((1,1,1,1)) == "1.1")
      self.assert_(previousRev((1,1,2,1)) == "1.1")
      self.assert_(previousRev((1,1,1,2)) == "1.1.1.1")
      self.assert_(previousRev((1,1,2,99)) == "1.1.2.98")
      self.assert_(previousRev((1,1,1,1,1,1)) == "1.1.1.1")
      self.assert_(previousRev((1,1,1,1,1,2)) == "1.1.1.1.1.1")



if __name__ == '__main__':
   unittest.main()
