import httplib2
import vobject

from django.conf import settings
from django.utils import simplejson as json

from contacts_import.backends.runners import AsyncRunner
from contacts_import.settings import RUNNER


# determine the base class based on what type of importing should be done
if issubclass(RUNNER, AsyncRunner):
    from celery.task import Task
else:
    Task = object


class BaseImporter(Task):
    def run(self, credentials, persistance):
        status = {
            "imported": 0,
            "total": 0,
        }
        for contact in self.get_contacts(credentials):
            status = persistance.persist(contact, status, credentials)
        return status


class VcardImporter(BaseImporter):
    def get_contacts(self, credentials):
        for card in vobject.readComponents(credentials["stream"]):
            try:
                yield {
                    "email": card.email.value,
                    "name": card.fn.value
                }
            except AttributeError:
                # if a person doesn't have an email or a name ignore them
                continue


class EmailListImporter(BaseImporter):
    def get_contacts(self, credentials):
        for email in credentials["stream"]:
            yield {
                "email": email,
                "name": '',
                }


class YahooImporter(BaseImporter):    
    def get_contacts(self, credentials):
        from oauth_access.access import OAuthAccess
        yahoo_token = credentials["yahoo_token"]
        access = OAuthAccess("yahoo")
        guid = access.make_api_call(
            "json",
            "http://social.yahooapis.com/v1/me/guid?format=json",
            yahoo_token
        )["guid"]["value"]
        address_book = access.make_api_call(
            "json",
            "http://social.yahooapis.com/v1/user/%s/contacts?format=json&count=max&view=tinyusercard" % guid,
            yahoo_token,
        )
        for contact in address_book["contacts"]["contact"]:
            # e-mail (if not found skip contact)
            try:
                email = self.get_field_value(contact, "email")
            except KeyError:
                continue
            # name (first and last comes together)
            try:
                name = self.get_field_value(contact, "name")
            except KeyError:
                name = ""
            if name:
                first_name = name["givenName"]
                last_name = name["familyName"]
                if first_name and last_name:
                    name = "%s %s" % (first_name, last_name)
                elif first_name:
                    name = first_name
                elif last_name:
                    name = last_name
                else:
                    name = ""
            yield {
                "email": email,
                "name": name,
            }
    
    def get_field_value(self, contact, kind):
        try:
            for field in contact["fields"]:
                if field["type"] == kind:
                    return field["value"]
        except KeyError:
            raise Exception("Yahoo data format changed")
        else:
            raise KeyError(kind)




from gdata.contacts.service import ContactsService
from gdata.auth import GenerateAuthSubUrl

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from contacts_import.settings import RUNNER, CALLBACK

GOOGLE_CONTACTS_URI = "http://www.google.com/m8/feeds/contacts/default/full?alt=json&max-results=1000"

class GoogleImporter(BaseImporter):
    def login_url(self, request):
        next = request.build_absolute_uri(reverse('import_google_contacts'))
        scope = 'http://www.google.com/m8/feeds/'
        return GenerateAuthSubUrl(next, scope, secure=False, session=True)

    def login_callback(self, request, redirect_to=None):
        if "token" in request.GET:
            token_login = request.GET["token"]
            gcs = ContactsService()
            gcs.SetAuthSubToken(token_login)
            request.session["authsub_token"] = gcs.GetAuthSubToken()

        return HttpResponseRedirect(request.build_absolute_uri())


    def import_contacts(self, request):
        runner_class = RUNNER
        authsub_token = request.session.pop("authsub_token", None)
        if authsub_token:
            runner = runner_class(GoogleImporter,
                                  user = request.user,
                                  authsub_token = authsub_token
                                  )
            results = runner.import_contacts()
            from ..views import _import_success
            return _import_success(request, results)


    def get_contacts(self, credentials):
        h = httplib2.Http()
        response, content = h.request(GOOGLE_CONTACTS_URI, headers={
            "Authorization": 'AuthSub token="%s"' % credentials["authsub_token"]
        })

        if response.status != 200:
            return

        results = json.loads(content)
        for person in results["feed"]["entry"]:
            for email in person.get("gd$email", []):
                yield {
                    "name": person["title"]["$t"],
                    "email": email["address"],
                }
