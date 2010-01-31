# vim:set tabstop=3 shiftwidth=3 expandtab:  
# vim:set autoindent smarttab nowrap:

from django.conf.urls.defaults import *
import settings

urlpatterns = patterns('',
    (r'^$',                               'webreview.views.index'),
    (r'^skip/(?P<skip>.*)$',              'webreview.views.changes'),
    (r'^diff/(?P<change_id>.*)/html$',    'webreview.views.diffhtml'),
    (r'^addmodule$',                      'webreview.views.addmodule'),
    (r'^login$',                          'webreview.views.login'),

    (r'^changes/all/skip/(?P<skip>\d+)$',                                'webreview.views.index'),
    (r'^changes/all$',                                                   'webreview.views.index'),
    (r'^changes/(?P<filter>.*)/(?P<filter_id>\d+)/skip/(?P<skip>\d*)$',  'webreview.views.changes'),
    (r'^changes/(?P<filter>.*)/(?P<filter_id>\d+)$',                     'webreview.views.changes'),

    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)
