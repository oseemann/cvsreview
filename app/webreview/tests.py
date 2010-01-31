#!/usr/bin/python2.5
# vim:set ts=3 sw=3 nowrap expandtab:  

import unittest
import views
from models import Change, Repository, User, File

class RefObjectTest(unittest.TestCase):
   def setUp(self):
      rep = Repository.objects.create(path="/test", name="test")
      file1 = File.objects.create(
         repository=rep, name="file1", last_change="2009-04-01 12:00:00", last_rev="1.5")
      file2 = File.objects.create(
         repository=rep, name="file2", last_change="2009-04-01 13:00:00", last_rev="2.1")
      user1 = User.objects.create(name="testuser")
      Change.objects.create(
         file=file1, user=user1, rev_old="1.4", rev_new="1.5",
         logmessage="Test Log Message", commit_time="2009-04-01 12:00:00", diffstat="+1 -0")
      Change.objects.create(
         file=file2, user=user1, rev_old="2.0", rev_new="2.1",
         logmessage="Test Log Message", commit_time="2009-04-01 12:00:00", diffstat="+1 -0")
      Change.objects.create(
         file=file1, user=user1, rev_old="1.3", rev_new="1.4",
         logmessage="A different message", commit_time="2009-04-01 09:00:00", diffstat="+1 -0")

   def testChanges(self):
      changesets = views.getchangesets()
      self.assertEqual(len(changesets), 2)
      set1 = changesets[0]
      set2 = changesets[1]
      self.assertEqual(len(set2), 1)
      self.assertEqual(len(set1), 2)
      self.assertEqual(set1[0].logmessage, set1[1].logmessage)
      self.assertEqual(set1[0].user, set1[1].user)
      self.assertNotEqual(set1[0].file, set1[1].file)

