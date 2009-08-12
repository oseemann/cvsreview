# -*-python-*-
#
# Copyright (C) 1999-2006 The ViewCVS Group. All Rights Reserved.
#
# By using this file, you agree to the terms and conditions set forth in
# the LICENSE.html file which can be found at the top level of the ViewVC
# distribution or at http://viewvc.org/license-1.html.
#
# For more information, visit http://viewvc.org/
#
# -----------------------------------------------------------------------

"Version Control lib driver for locally accessible cvs-repositories."

import vclib
import os
import os.path
import sys
import stat
import string
import re
import time

# ViewVC libs
import vclib.compat as compat

class CVSRepository(vclib.Repository):
  def __init__(self, name, rootpath):
    if not os.path.isdir(rootpath):
      raise vclib.ReposNotFound(name)

    self.name = name
    self.rootpath = rootpath

  def itemtype(self, path_parts, rev):
    basepath = self._getpath(path_parts)
    if os.path.isdir(basepath):
      return vclib.DIR
    if os.path.isfile(basepath + ',v'):
      return vclib.FILE
    atticpath = self._getpath(self._atticpath(path_parts))
    if os.path.isfile(atticpath + ',v'):
      return vclib.FILE
    raise vclib.ItemNotFound(path_parts)

  def listdir(self, path_parts, rev, options):
    # Only RCS files (*,v) and subdirs are returned.
    data = [ ]

    full_name = self._getpath(path_parts)
    for file in os.listdir(full_name):
      kind, errors = _check_path(os.path.join(full_name, file))
      if kind == vclib.FILE:
        if file[-2:] == ',v':
          data.append(CVSDirEntry(file[:-2], kind, errors, 0))
      elif kind == vclib.DIR:
        if file != 'Attic' and file != 'CVS': # CVS directory is for fileattr
          data.append(CVSDirEntry(file, kind, errors, 0))
      else:
        data.append(CVSDirEntry(file, kind, errors, 0))

    full_name = os.path.join(full_name, 'Attic')
    if os.path.isdir(full_name):
      for file in os.listdir(full_name):
        kind, errors = _check_path(os.path.join(full_name, file))
        if kind == vclib.FILE:
          if file[-2:] == ',v':
            data.append(CVSDirEntry(file[:-2], kind, errors, 1))
        elif kind != vclib.DIR:
          data.append(CVSDirEntry(file, kind, errors, 1))

    return data
    
  def _getpath(self, path_parts):
    return apply(os.path.join, (self.rootpath,) + tuple(path_parts))

  def _atticpath(self, path_parts):
    return path_parts[:-1] + ['Attic'] + path_parts[-1:]

  def rcsfile(self, path_parts, root=0, v=1):
    "Return path to RCS file"

    ret_parts = path_parts
    ret_file = self._getpath(ret_parts)
    if not os.path.isfile(ret_file + ',v'):
      ret_parts = self._atticpath(path_parts)
      ret_file = self._getpath(ret_parts)
      if not os.path.isfile(ret_file + ',v'):
        raise vclib.ItemNotFound(path_parts)

    if root:
      ret = ret_file
    else:
      ret = string.join(ret_parts, "/")

    if v:
      ret = ret + ",v"

    return ret

class CVSDirEntry(vclib.DirEntry):
  def __init__(self, name, kind, errors, in_attic):
    vclib.DirEntry.__init__(self, name, kind, errors)
    self.in_attic = in_attic

class Revision(vclib.Revision):
  def __init__(self, revstr, date=None, author=None, dead=None,
               changed=None, log=None):
    vclib.Revision.__init__(self, _revision_tuple(revstr), revstr,
                            date, author, changed, log, None)
    self.dead = dead

class Tag:
  def __init__(self, name, revstr):
    self.name = name
    self.number = _tag_tuple(revstr)
    self.is_branch = len(self.number) % 2 == 1 or not self.number


# ======================================================================
# Functions for dealing with Revision and Tag objects

def _match_revs_tags(revlist, taglist):
  """Match up a list of Revision objects with a list of Tag objects

  Sets the following properties on each Revision in revlist:
    "tags"
      list of non-branch tags which refer to this revision
      example: if revision is 1.2.3.4, tags is a list of all 1.2.3.4 tags

    "branches"
      list of branch tags which refer to this revision's branch
      example: if revision is 1.2.3.4, branches is a list of all 1.2.3 tags

    "branch_points"
      list of branch tags which branch off of this revision
      example: if revision is 1.2, it's a list of tags like 1.2.3 and 1.2.4

    "prev"
      reference to the previous revision, possibly None
      example: if revision is 1.2.3.4, prev is 1.2.3.3

    "next"
      reference to next revision, possibly None
      example: if revision is 1.2.3.4, next is 1.2.3.5

    "parent"
      reference to revision this one branches off of, possibly None
      example: if revision is 1.2.3.4, parent is 1.2

    "undead"
      If the revision is dead, then this is a reference to the first 
      previous revision which isn't dead, otherwise it's a reference
      to itself. If all the previous revisions are dead it's None. 

    "branch_number"
      tuple representing branch number or empty tuple if on trunk
      example: if revision is 1.2.3.4, branch_number is (1, 2, 3)

  Each tag in taglist gets these properties set:
    "co_rev"
      reference to revision that would be retrieved if tag were checked out

    "branch_rev"
      reference to revision branched off of, only set for branch tags
      example: if tag is 1.2.3, branch_rev points to 1.2 revision

    "aliases"
      list of tags that have the same number
  """

  # map of branch numbers to lists of corresponding branch Tags
  branch_dict = {}

  # map of revision numbers to lists of non-branch Tags
  tag_dict = {}

  # map of revision numbers to lists of branch Tags
  branch_point_dict = {}

  # toss tags into "branch_dict", "tag_dict", and "branch_point_dict"
  # set "aliases" property and default "co_rev" and "branch_rev" values
  for tag in taglist:
    tag.co_rev = None
    if tag.is_branch:
      tag.branch_rev = None
      _dict_list_add(branch_point_dict, tag.number[:-1], tag)
      tag.aliases = _dict_list_add(branch_dict, tag.number, tag)
    else:
      tag.aliases = _dict_list_add(tag_dict, tag.number, tag)

  # sort the revisions so the loop below can work properly
  revlist.sort()

  # array of the most recently encountered revision objects indexed by depth
  history = []

  # loop through revisions, setting properties and storing state in "history"
  for rev in revlist:
    depth = len(rev.number) / 2 - 1

    # set "prev" and "next" properties
    rev.prev = rev.next = None
    if depth < len(history):
      prev = history[depth]
      if prev and (depth == 0 or rev.number[:-1] == prev.number[:-1]):
        rev.prev = prev
        prev.next = rev

    # set "parent"
    rev.parent = None
    if depth and depth <= len(history):
      parent = history[depth-1]
      if parent and parent.number == rev.number[:-2]:
        rev.parent = history[depth-1]

    # set "undead"
    if rev.dead:
      prev = rev.prev or rev.parent
      rev.undead = prev and prev.undead
    else:
      rev.undead = rev

    # set "tags" and "branch_points"
    rev.tags = tag_dict.get(rev.number, [])
    rev.branch_points = branch_point_dict.get(rev.number, [])

    # set "branches" and "branch_number"
    if rev.prev:
      rev.branches = rev.prev.branches
      rev.branch_number = rev.prev.branch_number
    else:
      rev.branch_number = depth and rev.number[:-1] or ()
      try:
        rev.branches = branch_dict[rev.branch_number]
      except KeyError:
        rev.branches = []

    # set "co_rev" and "branch_rev"
    for tag in rev.tags:
      tag.co_rev = rev

    for tag in rev.branch_points:
      tag.co_rev = rev
      tag.branch_rev = rev

    # This loop only needs to be run for revisions at the heads of branches,
    # but for the simplicity's sake, it actually runs for every revision on
    # a branch. The later revisions overwrite values set by the earlier ones.
    for branch in rev.branches:
      branch.co_rev = rev

    # end of outer loop, store most recent revision in "history" array
    while len(history) <= depth:
      history.append(None)
    history[depth] = rev

def _add_tag(tag_name, revision):
  """Create a new tag object and associate it with a revision"""
  if revision:
    tag = Tag(tag_name, revision.string)
    tag.aliases = revision.tags
    revision.tags.append(tag)
  else:
    tag = Tag(tag_name, None)
    tag.aliases = []
  tag.co_rev = revision
  tag.is_branch = 0
  return tag

def _remove_tag(tag):
  """Remove a tag's associations"""
  tag.aliases.remove(tag)
  if tag.is_branch and tag.branch_rev:
    tag.branch_rev.branch_points.remove(tag)

def _revision_tuple(revision_string):
  """convert a revision number into a tuple of integers"""
  t = tuple(map(int, string.split(revision_string, '.')))
  if len(t) % 2 == 0:
    return t
  raise ValueError

def _tag_tuple(revision_string):
  """convert a revision number or branch number into a tuple of integers"""
  if revision_string:
    t = map(int, string.split(revision_string, '.'))
    l = len(t)
    if l == 1:
      return ()
    if l > 2 and t[-2] == 0 and l % 2 == 0:
      del t[-2]
    return tuple(t)
  return ()

def _dict_list_add(dict, idx, elem):
  try:
    list = dict[idx]
  except KeyError:
    list = dict[idx] = [elem]
  else:
    list.append(elem)
  return list


# ======================================================================
# Functions for parsing output from RCS utilities


class COMalformedOutput(vclib.Error):
  pass
class COMissingRevision(vclib.Error):
  pass

### suck up other warnings in _re_co_warning?
_re_co_filename = re.compile(r'^(.*),v\s+-->\s+(?:(?:standard output)|(?:stdout))\s*\n?$')
_re_co_warning = re.compile(r'^.*co: .*,v: warning: Unknown phrases like .*\n$')
_re_co_missing_rev = re.compile(r'^.*co: .*,v: revision.*absent\n$')
_re_co_side_branches = re.compile(r'^.*co: .*,v: no side branches present for [\d\.]+\n$')
_re_co_revision = re.compile(r'^revision\s+([\d\.]+)\s*\n$')

def _parse_co_header(fp):
  """Parse RCS co header.

  fp is a file (pipe) opened for reading the co standard error stream.

  Returns: (filename, revision) or (None, None) if output is empty
  """

  # header from co:
  #
  #/home/cvsroot/mod_dav/dav_shared_stub.c,v  -->  standard output
  #revision 1.1
  #
  # Sometimes, the following line might occur at line 2:
  #co: INSTALL,v: warning: Unknown phrases like `permissions ...;' are present.

  # parse the output header
  filename = None

  # look for a filename in the first line (if there is a first line).
  line = fp.readline()
  if not line:
    return None, None
  match = _re_co_filename.match(line)
  if not match:
    raise COMalformedOutput, "Unable to find filename in co output stream"
  filename = match.group(1)

  # look through subsequent lines for a revision.  we might encounter
  # some ignorable or problematic lines along the way.
  while 1:
    line = fp.readline()
    if not line:
      break
    # look for a revision.
    match = _re_co_revision.match(line)
    if match:
      return filename, match.group(1)
    elif _re_co_missing_rev.match(line) or _re_co_side_branches.match(line):
      raise COMissingRevision, "Got missing revision error from co output stream"
    elif _re_co_warning.match(line):
      pass
    else:
      break
    
  raise COMalformedOutput, "Unable to find revision in co output stream"

# if your rlog doesn't use 77 '=' characters, then this must change
LOG_END_MARKER = '=' * 77 + '\n'
ENTRY_END_MARKER = '-' * 28 + '\n'

_EOF_FILE = 'end of file entries'       # no more entries for this RCS file
_EOF_LOG = 'end of log'                 # hit the true EOF on the pipe
_EOF_ERROR = 'error message found'      # rlog issued an error

# rlog error messages look like
#
#   rlog: filename/goes/here,v: error message
#   rlog: filename/goes/here,v:123: error message
#
# so we should be able to match them with a regex like
#
#   ^rlog\: (.*)(?:\:\d+)?\: (.*)$
#
# But for some reason the windows version of rlog omits the "rlog: " prefix
# for the first error message when the standard error stream has been 
# redirected to a file or pipe. (the prefix is present in subsequent errors
# and when rlog is run from the console). So the expression below is more
# complicated
_re_log_error = re.compile(r'^(?:rlog\: )*(.*,v)(?:\:\d+)?\: (.*)$')

# CVSNT error messages look like:
# cvs rcsfile: `C:/path/to/file,v' does not appear to be a valid rcs file
# cvs [rcsfile aborted]: C:/path/to/file,v: No such file or directory
# cvs [rcsfile aborted]: cannot open C:/path/to/file,v: Permission denied
_re_cvsnt_error = re.compile(r'^(?:cvs rcsfile\: |cvs \[rcsfile aborted\]: )'
                             r'(?:\`(.*,v)\' |cannot open (.*,v)\: |(.*,v)\: |)'
                             r'(.*)$')

def _parse_log_header(fp):
  """Parse and RCS/CVS log header.

  fp is a file (pipe) opened for reading the log information.

  On entry, fp should point to the start of a log entry.
  On exit, fp will have consumed the separator line between the header and
  the first revision log.

  If there is no revision information (e.g. the "-h" switch was passed to
  rlog), then fp will consumed the file separator line on exit.

  Returns: filename, default branch, tag dictionary, rlog error message, 
  and eof flag
  """
  filename = head = branch = msg = ""
  taginfo = { }         # tag name => number

  parsing_tags = 0
  eof = None

  while 1:
    line = fp.readline()
    if not line:
      # the true end-of-file
      eof = _EOF_LOG
      break

    if parsing_tags:
      if line[0] == '\t':
        [ tag, rev ] = map(string.strip, string.split(line, ':'))
        taginfo[tag] = rev
      else:
        # oops. this line isn't tag info. stop parsing tags.
        parsing_tags = 0

    if not parsing_tags:
      if line[:9] == 'RCS file:':
        filename = line[10:-1]
      elif line[:5] == 'head:':
        head = line[6:-1]
      elif line[:7] == 'branch:':
        branch = line[8:-1]
      elif line[:14] == 'symbolic names':
        # start parsing the tag information
        parsing_tags = 1
      elif line == ENTRY_END_MARKER:
        # end of the headers
        break
      elif line == LOG_END_MARKER:
        # end of this file's log information
        eof = _EOF_FILE
        break
      else:
        error = _re_cvsnt_error.match(line)
        if error:
          p1, p2, p3, msg = error.groups()
          filename = p1 or p2 or p3
          if not filename:
            raise vclib.Error("Could not get filename from CVSNT error:\n%s"
                               % line)
          eof = _EOF_ERROR
          break

        error = _re_log_error.match(line)
        if error:
          filename, msg = error.groups()
          if msg[:30] == 'warning: Unknown phrases like ':
            # don't worry about this warning. it can happen with some RCS
            # files that have unknown fields in them (e.g. "permissions 644;"
            continue
          eof = _EOF_ERROR
          break

  return filename, branch, taginfo, msg, eof

_re_log_info = re.compile(r'^date:\s+([^;]+);'
                          r'\s+author:\s+([^;]+);'
                          r'\s+state:\s+([^;]+);'
                          r'(\s+lines:\s+([0-9\s+-]+);?)?'
                          r'(\s+commitid:\s+([a-zA-Z0-9]+))?\n$')
### _re_rev should be updated to extract the "locked" flag
_re_rev = re.compile(r'^revision\s+([0-9.]+).*')
def _parse_log_entry(fp):
  """Parse a single log entry.

  On entry, fp should point to the first line of the entry (the "revision"
  line).
  On exit, fp will have consumed the log separator line (dashes) or the
  end-of-file marker (equals).

  Returns: Revision object and eof flag (see _EOF_*)
  """
  rev = None
  line = fp.readline()
  if not line:
    return None, _EOF_LOG
  if line == LOG_END_MARKER:
    # Needed because some versions of RCS precede LOG_END_MARKER
    # with ENTRY_END_MARKER
    return None, _EOF_FILE
  if line[:8] == 'revision':
    match = _re_rev.match(line)
    if not match:
      return None, _EOF_LOG
    rev = match.group(1)

    line = fp.readline()
    if not line:
      return None, _EOF_LOG
    match = _re_log_info.match(line)

  eof = None
  log = ''
  while 1:
    line = fp.readline()
    if not line:
      # true end-of-file
      eof = _EOF_LOG
      break
    if line[:9] == 'branches:':
      continue
    if line == ENTRY_END_MARKER:
      break
    if line == LOG_END_MARKER:
      # end of this file's log information
      eof = _EOF_FILE
      break

    log = log + line

  if not rev or not match:
    # there was a parsing error
    return None, eof

  # parse out a time tuple for the local time
  tm = compat.cvs_strptime(match.group(1))

  # rlog seems to assume that two-digit years are 1900-based (so, "04"
  # comes out as "1904", not "2004").
  EPOCH = 1970
  if tm[0] < EPOCH:
    tm = list(tm)
    if (tm[0] - 1900) < 70:
      tm[0] = tm[0] + 100
    if tm[0] < EPOCH:
      raise ValueError, 'invalid year'
  date = compat.timegm(tm)

  return Revision(rev, date,
                  # author, state, lines changed
                  match.group(2), match.group(3) == "dead", match.group(5),
                  log), eof

def _skip_file(fp):
  "Skip the rest of a file's log information."
  while 1:
    line = fp.readline()
    if not line:
      break
    if line == LOG_END_MARKER:
      break

def _paths_eq(path1, path2):
  "See if two path strings are the same"
  # This function is neccessary because CVSNT (since version 2.0.29)
  # converts paths passed as arguments to use upper case drive
  # letter and forward slashes
  return os.path.normcase(path1) == os.path.normcase(path2)


# ======================================================================
# Functions for interpreting and manipulating log information

def _file_log(revs, taginfo, cur_branch, filter):
  """Augment list of Revisions and a dictionary of Tags"""

  # Add artificial ViewVC tag MAIN. If the file has a default branch, then
  # MAIN acts like a branch tag pointing to that branch. Otherwise MAIN acts
  # like a branch tag that points to the trunk. (Note: A default branch is
  # just a branch number specified in an RCS file that tells CVS and RCS
  # what branch to use for checkout and update operations by default, when
  # there's no revision argument or sticky branch to override it. Default
  # branches get set by "cvs import" to point to newly created vendor
  # branches. Sometimes they are also set manually with "cvs admin -b")
  taginfo['MAIN'] = cur_branch

  # Create tag objects
  for name, num in taginfo.items():
    taginfo[name] = Tag(name, num)
  tags = taginfo.values()

  # Set view_tag to a Tag object in order to filter results. We can filter by
  # revision number or branch number
  if filter:
    try:
      view_tag = Tag(None, filter)
    except ValueError:
      view_tag = None
    else:
      tags.append(view_tag)  

  # Match up tags and revisions
  _match_revs_tags(revs, tags)

  # Add artificial ViewVC tag HEAD, which acts like a non-branch tag pointing
  # at the latest revision on the MAIN branch. The HEAD revision doesn't have
  # anything to do with the "head" revision number specified in the RCS file
  # and in rlog output. HEAD refers to the revision that the CVS and RCS co
  # commands will check out by default, whereas the "head" field just refers
  # to the highest revision on the trunk.  
  taginfo['HEAD'] = _add_tag('HEAD', taginfo['MAIN'].co_rev)

  # Determine what revisions to return
  if filter:
    # If view_tag isn't set, it means filter is not a valid revision or
    # branch number. Check taginfo to see if filter is set to a valid tag
    # name. If so, filter by that tag, otherwise raise an error.
    if not view_tag:
      try:
        view_tag = taginfo[filter]
      except KeyError:
        raise vclib.Error('Invalid tag or revision number "%s"' % filter)
    filtered_revs = [ ]

    # only include revisions on the tag branch or it's parent branches
    if view_tag.is_branch:
      branch = view_tag.number
    elif len(view_tag.number) > 2:
      branch = view_tag.number[:-1]
    else:
      branch = ()

    # for a normal tag, include all tag revision and all preceding revisions.
    # for a branch tag, include revisions on branch, branch point revision,
    # and all preceding revisions
    for rev in revs:
      if (rev.number == view_tag.number
          or rev.branch_number == view_tag.number
          or (rev.number < view_tag.number
              and rev.branch_number == branch[:len(rev.branch_number)])):
        filtered_revs.append(rev)

    # get rid of the view_tag if it was only created for filtering
    if view_tag.name is None:
      _remove_tag(view_tag)
  else:
    filtered_revs = revs
  
  return filtered_revs

def _log_path(entry, dirpath, getdirs):
  path = name = None
  if not entry.errors:
    if entry.kind == vclib.FILE:
      path = entry.in_attic and 'Attic' or ''
      name = entry.name
    elif entry.kind == vclib.DIR and getdirs:
      entry.newest_file = _newest_file(os.path.join(dirpath, entry.name))
      if entry.newest_file:
        path = entry.name
        name = entry.newest_file

  if name:
    return os.path.join(dirpath, path, name + ',v')
  return None


# ======================================================================
# Functions for dealing with the filesystem

if sys.platform == "win32":
  def _check_path(path):
    kind = None
    errors = []

    if os.path.isfile(path):
      kind = vclib.FILE
    elif os.path.isdir(path):
      kind = vclib.DIR
    else:
      errors.append("error: path is not a file or directory")

    if not os.access(path, os.R_OK):
      errors.append("error: path is not accessible")

    return kind, errors

else:
  _uid = os.getuid()
  _gid = os.getgid()

  def _check_path(pathname):
    try:
      info = os.stat(pathname)
    except os.error, e:
      return None, ["stat error: %s" % e]

    kind = None
    errors = []

    mode = info[stat.ST_MODE]
    isdir = stat.S_ISDIR(mode)
    isreg = stat.S_ISREG(mode)
    if isreg or isdir:
      #
      # Quick version of access() where we use existing stat() data.
      #
      # This might not be perfect -- the OS may return slightly different
      # results for some bizarre reason. However, we make a good show of
      # "can I read this file/dir?" by checking the various perm bits.
      #
      # NOTE: if the UID matches, then we must match the user bits -- we
      # cannot defer to group or other bits. Similarly, if the GID matches,
      # then we must have read access in the group bits.
      #
      # If the UID or GID don't match, we need to check the
      # results of an os.access() call, in case the web server process
      # is in the group that owns the directory.
      #
      if isdir:
        mask = stat.S_IROTH | stat.S_IXOTH
      else:
        mask = stat.S_IROTH

      if info[stat.ST_UID] == _uid:
        if ((mode >> 6) & mask) != mask:
          errors.append("error: path is not accessible to user %i" % _uid)
      elif info[stat.ST_GID] == _gid:
        if ((mode >> 3) & mask) != mask:
          errors.append("error: path is not accessible to group %i" % _gid)
      # If the process running the web server is a member of
      # the group stat.ST_GID access may be granted.
      # so the fall back to os.access is needed to figure this out.
      elif (mode & mask) != mask:
        if not os.access(pathname, isdir and (os.R_OK | os.X_OK) or os.R_OK):
          errors.append("error: path is not accessible")

      if isdir:
        kind = vclib.DIR
      else:
        kind = vclib.FILE

    else:
      errors.append("error: path is not a file or directory")

    return kind, errors

def _newest_file(dirpath):
  """Find the last modified RCS file in a directory"""
  newest_file = None
  newest_time = 0

  for subfile in os.listdir(dirpath):
    ### filter CVS locks? stale NFS handles?
    if subfile[-2:] != ',v':
      continue
    path = os.path.join(dirpath, subfile)
    info = os.stat(path)
    if not stat.S_ISREG(info[stat.ST_MODE]):
      continue
    if info[stat.ST_MTIME] > newest_time:
      kind, verboten = _check_path(path)
      if kind == vclib.FILE and not verboten:
        newest_file = subfile[:-2]
        newest_time = info[stat.ST_MTIME]

  return newest_file
