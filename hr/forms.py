from django import forms
from hr.models import ( CompanyName, Department, SubDepartment, Category,
                       Qualification, Designation, ZoneofOperations, Employee,Assets, Branches)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    first_name = forms.CharField(max_length=100, label="First Name")
    last_name = forms.CharField(max_length=100, required=False, label="Last Name")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password', 'confirm_password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"] or ''

        if commit:
            user.save()
        return user


class CompanyNameForm(forms.ModelForm):
    class Meta:
        model = CompanyName
        fields = ['company_name', 'status']

        widgets = {
            # "company_name":forms.Textarea(attrs={"class":"form-control"}),
            # "status":forms.Select(attrs={"class":"form-control"}),
        }

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['department_name', 'company_name', 'status']
        widgets = {
            'department_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}, choices=[('active', 'Active'), ('inactive', 'Inactive')])
        }

class SubDepartmentForm(forms.ModelForm):
    class Meta:
        model = SubDepartment
        fields = ['sub_department_name', 'department_name', 'company_name', 'status']



class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_name', 'company_name', 'department_name', 'sub_department_name', 'status']


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ['qualification_name', 'status']


class ZoneofOperationsForm(forms.ModelForm):
    class Meta:
        model = ZoneofOperations
        fields = ['name', 'status']

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'

class AssetsForm(forms.ModelForm):
    class Meta:
        model = Assets
        fields = ['name', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class EmployeeUpgradeForm(forms.Form):
    # Rating Update
    rating = forms.ChoiceField(
        choices=Employee.RATING_CHOICES,
        required=False,
        label="Employee Rating",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Branch Transfer
    new_branch = forms.ModelChoiceField(
        queryset=Branches.objects.filter(status='active'),
        required=False,
        label="New Branch",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Branch"
    )
    branch_transfer_reason = forms.CharField(
        required=False,
        label="Reason for Branch Transfer",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    # Salary Increment
    new_salary = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="New Salary",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    salary_increment_reason = forms.CharField(
        required=False,
        label="Reason for Salary Increment",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    # Promotion
    new_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(status='active'),
        required=False,
        label="New Department",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Department"
    )
    new_sub_department = forms.ModelChoiceField(
        queryset=SubDepartment.objects.filter(status='active'),
        required=False,
        label="New Sub-Department",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Sub-Department"
    )
    new_category = forms.ModelChoiceField(
        queryset=Category.objects.filter(status='active'),
        required=False,
        label="New Category",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Category"
    )
    new_designation = forms.ModelChoiceField(
        queryset=Designation.objects.filter(status='active'),
        required=False,
        label="New Designation",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Designation"
    )
    promotion_remarks = forms.CharField(
        required=False,
        label="Promotion Remarks",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def clean(self):
        cleaned_data = super().clean()
        # Ensure at least one upgrade field is provided
        rating = cleaned_data.get('rating')
        new_branch = cleaned_data.get('new_branch')
        new_salary = cleaned_data.get('new_salary')
        new_department = cleaned_data.get('new_department')
        new_sub_department = cleaned_data.get('new_sub_department')
        new_category = cleaned_data.get('new_category')
        new_designation = cleaned_data.get('new_designation')

        if not any([rating, new_branch, new_salary, new_department, new_sub_department, new_category, new_designation]):
            raise forms.ValidationError("At least one upgrade action (rating, branch, salary, or promotion) must be provided.")

        return cleaned_data
