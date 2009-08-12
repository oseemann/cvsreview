# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

from django.conf.urls.defaults import *
import settings

urlpatterns = patterns('',
    (r'^$',                               'cvsreview.webreview.views.index'),
    (r'^skip/(?P<skip>.*)$',              'cvsreview.webreview.views.changes'),
    (r'^diff/(?P<change_id>.*)/html$',    'cvsreview.webreview.views.diffhtml'),
    (r'^addmodule$',                      'cvsreview.webreview.views.addmodule'),
    (r'^login$',                          'cvsreview.webreview.views.login'),

    (r'^changes/all/skip/(?P<skip>\d+)$',                                'cvsreview.webreview.views.index'),
    (r'^changes/all$',                                                   'cvsreview.webreview.views.index'),
    (r'^changes/(?P<filter>.*)/(?P<filter_id>\d+)/skip/(?P<skip>\d*)$',  'cvsreview.webreview.views.changes'),
    (r'^changes/(?P<filter>.*)/(?P<filter_id>\d+)$',                     'cvsreview.webreview.views.changes'),

    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)
