from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Option, Poll


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class PollForm(forms.ModelForm):
    options = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 7,
                "placeholder": "One answer option per line",
                "maxlength": "18100",
            }
        ),
        help_text="Put each answer option on its own line. Add 2–100 options.",
    )

    class Meta:
        model = Poll
        fields = ("question", "description", "category", "visibility")
        widgets = {
            "question": forms.TextInput(
                attrs={"placeholder": "What do you want to ask?", "maxlength": "220"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Add a little context (optional)"}
            ),
        }

    def clean_options(self):
        options = [
            line.strip()
            for line in self.cleaned_data["options"].splitlines()
            if line.strip()
        ]
        if len(options) < 2:
            raise forms.ValidationError("Please add at least two answer options.")
        if len(options) > 100:
            raise forms.ValidationError("A poll can have up to 100 options.")
        if any(len(option) > 180 for option in options):
            raise forms.ValidationError("Each option must be 180 characters or fewer.")
        normalized = [option.casefold() for option in options]
        if len(normalized) != len(set(normalized)):
            raise forms.ValidationError("Each answer option must be different.")
        return options


class VoteForm(forms.Form):
    option = forms.ModelChoiceField(
        queryset=Option.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
    )

    def __init__(self, *args, poll, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["option"].queryset = poll.options.all()


class ProfileForm(forms.Form):
    bio = forms.CharField(
        max_length=240,
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "A little about you...", "maxlength": "240"}
        ),
    )
