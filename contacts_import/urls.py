from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^import_contacts/$", "contacts_import.views.import_contacts", name="import_contacts"),
    url(r"^import_google_contacts/$", "contacts_import.views.import_google_contacts", name="import_google_contacts"),
    url(r"^select_contacts/$", "contacts_import.views.select_contacts", name="select_contacts"),
                       #url(r"^authsub/login/$", "contacts_import.views.authsub_login", name="authsub_login"),
)
