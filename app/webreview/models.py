# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

from django.db import models
from datetime import timedelta, datetime

import re

# Create your models here.
class Category(models.Model):
   name = models.CharField(max_length=30)

class Repository(models.Model):
   path = models.TextField()
   name = models.CharField(max_length=100)
   category = models.ForeignKey(Category, null=True)

class File(models.Model):
   repository = models.ForeignKey('Repository') 
   name = models.CharField(max_length=250)
   last_change = models.DateTimeField()
   last_rev = models.CharField(max_length=20, null=True)

class User(models.Model):
   name = models.CharField(max_length=40)

class Branch(models.Model):
   tag = models.CharField(max_length=100)
   name = models.CharField(max_length=30)
    
class Change(models.Model):
   file = models.ForeignKey('File')
   user = models.ForeignKey('User')
   rev_old = models.CharField(max_length=20)
   rev_new = models.CharField(max_length=20)
   logmessage = models.TextField()
   commit_time = models.DateTimeField()
   diffstat = models.CharField(max_length=40)

   loglenlimit = 200
   loglenshort = 190

   def logisshort(self):
      return (len(self.logmessage) < self.loglenlimit)

   def longlog(self):
      return self.logmessage
   
   def shortlog(self):
      if self.logisshort():
         return self.logmessage
      else:
         return self.logmessage[:self.loglenshort]

   def commit_time_nice(self):
      delta = datetime.now() - self.commit_time
      if delta < timedelta(minutes=1):
         val = delta.seconds
         ret = "%d second" % (val)
      elif delta < timedelta(hours=1):
         val = delta.seconds/60
         ret = "%d minute" % (val)
      elif delta < timedelta(days=1):
         val = delta.seconds/3600
         ret = "%d hour" % (val)
      else:
         val = delta.days
         ret = "%d day" % (val)

      if val > 1:
         ret += "s"
      ret += " ago"
      return ret

   def sameset(self, other):
      return self.user == other.user and self.logmessage == other.logmessage

class Comment(models.Model):
   change = models.ForeignKey('Change')
   user = models.ForeignKey('User')
   text = models.TextField()
   timestamp = models.DateTimeField()

