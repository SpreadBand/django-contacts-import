from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^import_contacts/$', views.import_contacts, name='import_contacts'),

    # Backends
    url(r'^import_google_contacts/$', views.import_google_contacts, name='import_google_contacts'),
    url(r'^import_email_list/$', views.import_email_list, name='import_email_list'),

    # Contact selection
    url(r'^select_contacts/$', views.select_contacts, name='select_contacts'),
)
