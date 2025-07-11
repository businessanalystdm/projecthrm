from django import forms
from .models import CustomUser

class SignUpForm(forms.ModelForm):
    password=forms.CharField(widget=forms.PasswordInput, label="Password:")
    confirm_password=forms.CharField(widget=forms.PasswordInput, label="Confirm Password:")

    class Meta:
        model=CustomUser
        fields=['first_name','last_name','username','email','password']
        labels={
            'first_name' : 'First Name:',
            'last_name': 'Last Name:',
            'username' : 'Username:',
            'email' : 'Email:'
        }
    def clean(self):
        cleaned_data=super().clean()
        password=cleaned_data.get("password")
        confirm_password=cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Password Doesnt Match.")
        return cleaned_data

    def save(self, commit=True):
        user=super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class SignInForm(forms.Form):
    username=forms.CharField(label="Username:")
    password=forms.CharField(widget=forms.PasswordInput, label="Password:")

