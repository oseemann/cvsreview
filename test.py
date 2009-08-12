import vclib.ccvs

def getbranchname(repo, file, rev):
  opt = {}
  revs = repo.itemlog([file], rev, opt)
  for r in revs:
    blist = [b for b in r.branches if b.is_branch == True and b.number]
  return blist[0].name

path = "/home/extcvsrepos/packages/src/libraries/cutils/"
repo = vclib.ccvs.CCVSRepository("foo", path)

#name = getbranchname(repo, "Changes", "1.50.2.8")
#print name
#for entry in repo.listdir(["./src/cutils"], None, {}):

revs = repo.itemlog(["./src/cutils/Attic/heapconfigset_impl.c"], None, {})
print len(revs)
