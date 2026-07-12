from django import forms
from .models import User, Event


class StudentSignupForm(forms.Form):
    name = forms.CharField(max_length=80, min_length=2)
    email = forms.EmailField()
    college = forms.CharField(max_length=120, min_length=2)
    age = forms.IntegerField(min_value=15, max_value=100)
    password = forms.CharField(min_length=6, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class AdminRequestForm(forms.Form):
    name = forms.CharField(max_length=80, min_length=2)
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        existing = User.objects.filter(email=email).first()
        if existing:
            if existing.admin_request_status == "pending":
                raise forms.ValidationError(
                    "An admin request for this email is already pending."
                )
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(min_length=6, widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        new = data.get("new_password")
        confirm = data.get("confirm_password")
        current = data.get("current_password")
        if new and confirm and new != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        if new and current and new == current:
            self.add_error("new_password", "New password must be different.")
        return data


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "department", "venue",
            "date", "capacity", "organizer", "banner_color",
        ]
        widgets = {
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
            "banner_color": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the datetime input accept the browser's local format.
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]
        self.fields["capacity"].required = False
        self.fields["organizer"].required = False
