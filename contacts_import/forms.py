import re

from django import forms
from django.core.validators import validate_email
from django.utils.translation import ugettext as _

from .backends.importers import VcardImporter, EmailListImporter
from .backends.runners import SynchronousRunner

class VcardImportForm(forms.Form):
    vcard_file = forms.FileField(label=_("vCard File"))
    
    def save(self, user, runner_class=SynchronousRunner):
        importer = runner_class(VcardImporter,
                                user = user,
                                stream = self.cleaned_data["vcard_file"]
                                )
        return importer.import_contacts()


class EmailListImportForm(forms.Form):
    """
    Form for importing a list of comma-separated email adresses
    """
    emails = forms.CharField(label=_("email adresses"),
                             widget=forms.Textarea,
                             )

    def clean_emails(self):
        emails = self.cleaned_data.get('emails')

        # Remove whitespaces
        emails = re.sub(r'\s', '', emails)
       
        # Split emails to get a list and validate them against the
        # django email validator
        email_list = emails.split(",")
        [validate_email(email) for email in email_list]

        return email_list

    def save(self, user, runner_class=SynchronousRunner):
        importer = runner_class(EmailListImporter,
                                user = user,
                                stream = self.cleaned_data.get('emails')
                                )

        return importer.import_contacts()
