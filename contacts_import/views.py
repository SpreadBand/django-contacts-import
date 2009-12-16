from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from django.contrib.auth.decorators import login_required

from gdata.contacts.service import ContactsService

from contacts_import.forms import VcardImportForm
from contacts_import.backends.importers import GoogleImporter, YahooImporter
from contacts_import.backends.runners import SynchronousRunner, AsyncRunner


GOOGLE_CONTACTS_URI = "http://www.google.com/m8/feeds/"


def _import_success(request, results):
    if results.ready():
        if results.status == "DONE":
            request.user.message_set.create(message=_(
                "%(total)s people with email found, %(imported)s contacts imported."
            ) % results.result)
        elif results.status == "FAILURE":
            request.user.message_set.create(message=_("There was an error "
                "importing your contacts."))
    else:
        request.user.message_set.create(message=_("We're still importing your "
            "contacts.  We'll let you know when they're ready, it shouldn't "
            "take too long."))
        request.session["import_contacts_task_id"] = results.task_id
    return HttpResponseRedirect(request.path)


@login_required
def import_contacts(request, runner_class=AsyncRunner):
    if request.method == "POST":
        if request.POST["action"] == "upload_vcard":
            form = VcardImportForm(request.POST)
            if form.is_valid():
                results = form.save(request.user, runner_class=runner_class)
                return _import_success(request, results)
        else:
            form = VcardImportForm()
            if request.POST["action"] == "import_yahoo":
                bbauth_token = request.session.pop("bbauth_token", None)
                if bbauth_token:
                    results = runner_class(YahooImporter, user=request.user,
                        bbauth_token=bbauth_token).import_contacts()
                    return _import_success(request, results)
            elif request.POST["action"] == "import_google":
                authsub_token = request.session.pop("authsub_token", None)
                if authsub_token:
                    results = runner_class(GoogleImporter, user=request.user,
                        authsub_token=authsub_token).import_contacts()
                    return _import_success(request,  results)
    else:
        form = VcardImportForm()
    
    contacts = request.user.contacts.all()
    page = Paginator(contacts, 50).page(request.GET.get("page", 1))
    
    return render_to_response("contacts_import/import_contacts.html", {
        "form": form,
        "bbauth_token": request.session.get("bbauth_token"),
        "authsub_token": request.session.get("authsub_token"),
        "page": page,
        "task_id": request.session.pop("import_contacts_task_id", None),
    }, context_instance=RequestContext(request))


def _authsub_url(next):
    contacts_service = ContactsService()
    return contacts_service.GenerateAuthSubURL(next, GOOGLE_CONTACTS_URI, False, True)


def authsub_login(request, redirect_to=None):
    if redirect_to is None:
        redirect_to = reverse("import_contacts")
    if "token" in request.GET:
        request.session["authsub_token"] = request.GET["token"]
        return HttpResponseRedirect(redirect_to)
    return HttpResponseRedirect(_authsub_url(request.build_absolute_uri()))