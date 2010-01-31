# Create your views here.
# vim:set tabstop=4 shiftwidth=4 expandtab:  
# vim:set autoindent smarttab nowrap:

import vclib.ccvs
import django.http as http
from django.shortcuts import render_to_response
from webreview.models import File, Repository, Change, User, Comment, Category

class Navigation:
    def __init__(self, max, offset):
        self.max = max
        self.limit = 100
        self.offset = offset
        self.nextoffset = self.offset + self.limit
        self.prevoffset = self.offset - self.limit
        if self.prevoffset < 0:
            self.prevoffset = 0
        self.hasprev = (self.offset > 0)
        self.hasnext = (self.max >= self.limit)

def getchangesets(category=None, module=None, skip=0):
    limit = 100 + int(skip)
    order = '-commit_time'
    if category:
        mods = Repository.objects.filter(category=category)
        changes = Change.objects.filter(file__repository__in=mods).order_by(order)[skip:limit]
    elif module:
        changes = Change.objects.filter(file__repository=module).order_by(order)[skip:limit]
    else:
        changes = Change.objects.all().order_by(order)[skip:limit]
    lastday = None
    # mark date borders
    for change in changes:
        change.newday = (change.commit_time.day != lastday)
        lastday = change.commit_time.day
    # group changes by commit message
    i = 0
    changesets = [[c] for c in changes]
    while i < len(changesets)-1:
        if changesets[i][0].sameset(changesets[i+1][0]):
            changesets[i] += changesets.pop(i+1)
        else:
            i += 1
    return changesets

def diffhtml(request, change_id):
    class Line: pass
    change = Change.objects.get(id=change_id)
    module = vclib.ccvs.CCVSRepository("foo", change.file.repository.path)
    diff = module.rawdiff(
                [change.file.name], change.rev_old,
                [change.file.name], change.rev_new, 1)
    difflines = []
    line = diff.readline()
    while line != '':
        l = Line()
        l.str=line
        if line[0] == '+' and len(difflines)>2:
            l.diffin = True
        if line[0] == '-' and len(difflines)>2:
            l.diffout = True
        difflines.append(l)
        line = diff.readline().replace(" ", "&nbsp;").replace("<", "&lt;")
        
    vars = {
        'difflines': difflines,
    }
    return render_to_response('diff.html', vars)

def getcategories():
    categories = Category.objects.all().order_by('name')
    for cat in categories:
        mods = Repository.objects.filter(category=cat).order_by('name')
        cat.modules = mods
    return categories

def index(request, skip=0):
    return changes(request, skip=skip)

def changes(request, filter=None, filter_id=None, skip=0):
    skip = int(skip)
    module = None
    category = None
    if filter == 'module':
        module = Repository.objects.get(id=filter_id)
        changesets = getchangesets(module=module, skip=skip)
        url = '/changes/module/%d' % module.id
    elif filter == 'category':
        category = Category.objects.get(id=filter_id)
        changesets = getchangesets(category=category, skip=skip)
        url = '/changes/category/%d' % category.id
    else:
        url = '/changes/all'
        changesets = getchangesets(skip=skip)
    categories = getcategories()
    # the reduce clause returns the total number of changes in the changesets
    nav = Navigation(reduce(lambda x, y: x+len(y), changesets, 0), skip)
    vars = {
        'category_list': categories,
        'changesets': changesets,
        'module': module,
        'category': category,
        'navigation': nav,
        'url': url,
    }
    return render_to_response('index.html', vars )

def addmodule(request):
    name = ''
    path = ''
    catid = ''
    if 'name' in request.GET:
        name = request.GET['name']
    if 'path' in request.GET:
        path = request.GET['path']
    if 'cat' in request.GET:
        catid = request.GET['cat']
    try:
        qsname = Repository.objects.filter(name=name) 
        qspath = Repository.objects.filter(path=path) 
        category = Category.objects.get(id=catid)
        if len(qspath) > 0:
            status = 'pathexist'
        elif len(qsname) > 0:
            status = 'nameexist'
        elif len(name) == 0:
            status = 'nameinvalid'
        elif len(path) == 0:
            status = 'pathinvalid'
        elif not category:
            status = 'catinvalid'
        else:
            try:
                module = vclib.ccvs.CCVSRepository("foo", path)
                status = 'ok'
            except:
                status = 'notexist'

        if status == 'ok':
            newmodule = Repository()
            newmodule.name = name
            newmodule.path = path
            newmodule.category = category
            newmodule.save()
    except:
        status = 'error'

    content = '{"status":"%s"}' % status
    content_type = "text/plain"
    return http.HttpResponse(content, mimetype=str(content_type))

