from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator, EmailValidator
from django.core.validators import MinValueValidator
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class CompanyName(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending')
    ]
    company_name = models.CharField(max_length=100, null=False, blank=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return self.company_name


class Department(models.Model):
    department_name = models.CharField(max_length=255)
    company_name = models.ForeignKey(CompanyName, on_delete=models.CASCADE, related_name='departments')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return self.department_name

    class Meta:
        pass  # Removed unique_together


class SubDepartment(models.Model):
    sub_department_name = models.CharField(max_length=100, null=False, blank=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sub_departments')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return self.sub_department_name

    def clean(self):
        pass

    class Meta:
        pass  # Removed unique_together


class Category(models.Model):
    category_name = models.CharField(max_length=100, null=False, blank=False)
    sub_department = models.ForeignKey(SubDepartment, on_delete=models.CASCADE, related_name='categories')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return self.category_name

    def clean(self):
        pass

    class Meta:
        pass  # Removed unique_together


class Designation(models.Model):
    designation_name = models.CharField(max_length=100, null=True, blank=True)
    rank = models.IntegerField(default=1, null=False, blank=False,
                               help_text="Priority for sorting (lower numbers appear first)")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='designations')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return self.designation_name

    def clean(self):
        pass

    class Meta:
        pass  # Removed unique_together


class Qualification(models.Model):
    qualification_name = models.CharField(max_length=100, null=False, blank=False)
    status = models.CharField(
        max_length=20,
        default='active',
        choices=[('active', 'Active'), ('inactive', 'Inactive')]
    )

    def __str__(self):
        return self.qualification_name


class ZoneofOperations(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')])

    def __str__(self):
        return self.name


class Branches(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    code = models.CharField(
        max_length=5,
        null=False,
        blank=False,
        validators=[RegexValidator(r'^[A-Z]+$', 'Only uppercase letters are allowed.')],
    )
    zone = models.ForeignKey(ZoneofOperations, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')])

    def __str__(self):
        return self.name


class Assets(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')])


class Skill(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    emp_id_branch = models.CharField(
        max_length=7,
        unique=True,
        blank=False,
        null=False,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$',
                message="Employee ID must be exactly 7 digits."
            )
        ],
        verbose_name="Employee ID"
    )
    emp_first_name = models.CharField(max_length=100, blank=False, null=False)
    emp_last_name = models.CharField(max_length=100, blank=True, null=True)
    emp_photo = models.ImageField(upload_to='employee_photo/', blank=True, null=True)
    emp_dob = models.DateField(blank=False, null=False)
    emp_gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female')
        ],
        blank=False,
        null=False
    )
    emp_address = models.TextField(blank=False, null=False)
    emp_mobile = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?\d{10,15}$', message="Enter a valid phone number.")], blank=False,
        null=False
    )
    emp_second_mobile = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?\d{10,15}$', message="Enter a valid phone number.")], blank=True,
        null=True
    )
    emp_qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
    emp_email = models.EmailField(
        blank=False, null=False,
        validators=[EmailValidator(message="Enter a valid email address.")],
    )
    emp_company = models.ForeignKey(CompanyName, on_delete=models.CASCADE)
    emp_department = models.ForeignKey(Department, on_delete=models.CASCADE)
    emp_sub_department = models.ForeignKey(SubDepartment, on_delete=models.CASCADE)
    emp_designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    emp_extra_skills = models.ManyToManyField(Skill)
    emp_salary = models.DecimalField(blank=False, null=False, max_digits=10, decimal_places=2,
                                     verbose_name="Employee Salary")
    emp_branch = models.ForeignKey(Branches, on_delete=models.CASCADE)
    emp_blood_group = models.CharField(
        max_length=5,
        choices=[
            ('ab+ve', 'AB+'), ('ab-ve', 'AB-'),
            ('a+ve', 'A+'), ('a-ve', 'A-'),
            ('b+ve', 'B+'), ('b-ve', 'B-'),
            ('o+ve', 'O+'), ('o-ve', 'O-')
        ]
    )
    emp_joining_date = models.DateField(blank=False, null=False)
    emp_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    emp_resigning_date = models.DateField(blank=True, null=True)
    emp_resigning_reason = models.TextField(blank=True, null=True, help_text="Reason for employee's resignation")
    emp_documents = models.FileField(upload_to='employee_documents/', blank=True, null=True,
                                     help_text="Upload employee documents")
    emp_status = models.CharField(max_length=100, blank=False, null=False,
                                  choices=[('active', 'Active'), ('in-active', 'In Active')], default='active', )
    RATING_CHOICES = [
        ('poor', 'Poor'),
        ('bad', 'Bad'),
        ('average', 'Average'),
        ('good', 'Good'),
        ('excellent', 'Excellent')
    ]
    emp_rating = models.CharField(max_length=20, blank=True, null=True, choices=RATING_CHOICES, default='average')
    emp_last_rating_date = models.DateField(blank=True, null=True, help_text="Date of the last rating")

    @property
    def is_rating_due(self):
        if not self.emp_joining_date:
            return False
        if not self.emp_last_rating_date:
            return self.emp_joining_date + relativedelta(months=3) <= date.today()
        return self.emp_last_rating_date + relativedelta(months=3) <= date.today()

    def __str__(self):
        return f"{self.emp_first_name} {self.emp_last_name or ''}"

    @property
    def work_duration(self):
        if not self.emp_joining_date:
            return 0
        end_date = self.emp_resigning_date or date.today()
        duration = (end_date - self.emp_joining_date).days
        return max(duration, 0)

    emp_experiences = models.JSONField(blank=True, null=True, default=list)
    emp_work_start_time = models.TimeField(blank=False, null=False)
    emp_work_end_time = models.TimeField(blank=False, null=False)
    emp_aadhar_number = models.CharField(max_length=12, blank=False, null=True)
    emp_assets = models.ManyToManyField(Assets, blank=True)
    emp_remarks = models.TextField(blank=True, null=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            try:
                # Create BranchHistory
                if self.emp_branch and self.emp_joining_date:
                    BranchHistory.objects.create(
                        employee=self,
                        branch=self.emp_branch,
                        start_date=self.emp_joining_date,
                        status='active'
                    )
                    logger.info(f"Created BranchHistory for employee {self.id}")

                # Create SalaryIncrementHistory
                if self.emp_salary and self.emp_joining_date:
                    if not SalaryIncrementHistory.objects.filter(
                            employee=self,
                            start_date=self.emp_joining_date,
                            end_date__isnull=True
                    ).exists():
                        SalaryIncrementHistory.objects.create(
                            employee=self,
                            salary=self.emp_salary,
                            start_date=self.emp_joining_date,
                            end_date=None,
                            status='active'
                        )
                        logger.info(f"Created SalaryIncrementHistory for employee {self.id}")

                # Create initial PromotionHistory
                if all([self.emp_department, self.emp_sub_department, self.emp_category, self.emp_designation,
                        self.emp_joining_date]):
                    # Close any existing active promotions
                    existing_promotions = PromotionHistory.objects.select_for_update().filter(
                        employee=self,
                        end_date__isnull=True,
                        status='active'
                    )
                    for promotion in existing_promotions:
                        promotion.end_date = self.emp_joining_date - timedelta(days=1)
                        promotion.status = 'inactive'
                        promotion.save()
                        logger.warning(f"Closed existing active promotion {promotion.id} for employee {self.id}")

                    # Create new PromotionHistory if none exists for this employee
                    if not PromotionHistory.objects.filter(employee=self).exists():
                        PromotionHistory.objects.create(
                            employee=self,
                            department=self.emp_department,
                            sub_department=self.emp_sub_department,
                            category=self.emp_category,
                            designation=self.emp_designation,
                            start_date=self.emp_joining_date,
                            end_date=None,
                            status='active'
                        )
                        logger.info(f"Created initial PromotionHistory for employee {self.id}")
            except Exception as e:
                logger.error(f"Error creating history records for employee {self.id}: {str(e)}")
                raise


class BranchHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='branch_history')
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE)
    start_date = models.DateField(blank=False, null=False, help_text="Start date of branch assignment")
    end_date = models.DateField(blank=True, null=True, help_text="End date of branch assignment (null if current)")
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        help_text="Status of this branch assignment"
    )

    def __str__(self):
        return f"{self.employee} - {self.branch.name} ({self.start_date} to {self.end_date or 'Present'})"

    class Meta:
        verbose_name = "Branch History"
        verbose_name_plural = "Branch Histories"
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['employee', 'end_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')) | models.Q(end_date__isnull=True),
                name='end_date_gte_start_date'
            )
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class SalaryIncrementHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_increment_history')
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=False,
        null=False,
        validators=[MinValueValidator(0.01)],
        verbose_name="New Salary"
    )
    start_date = models.DateField(blank=False, null=False, help_text="Start date of salary increment")
    end_date = models.DateField(blank=True, null=True, help_text="End date of salary increment (null if current)")
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        help_text="Status of this salary increment"
    )

    def __str__(self):
        return f"{self.employee} - {self.salary} ({self.start_date} to {self.end_date or 'Present'})"

    class Meta:
        verbose_name = "Salary Increment History"
        verbose_name_plural = "Salary Increment Histories"
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['employee', 'end_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')) | models.Q(end_date__isnull=True),
                name='salary_end_date_gte_start_date'
            ),
            models.CheckConstraint(
                check=models.Q(salary__gt=0),
                name='salary_positive'
            )
        ]


class PromotionHistory(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='promotion_history')
    department = models.ForeignKey('Department', on_delete=models.CASCADE)
    sub_department = models.ForeignKey('SubDepartment', on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    designation = models.ForeignKey('Designation', on_delete=models.CASCADE)
    start_date = models.DateField(blank=False, null=False, help_text="Start date of promotion")
    end_date = models.DateField(blank=True, null=True, help_text="End date of promotion (null if current)")
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        help_text="Status of this promotion"
    )

    def __str__(self):
        return f"{self.employee} - {self.designation.designation_name} ({self.start_date} to {self.end_date or 'Present'})"

    class Meta:
        verbose_name = "Promotion History"
        verbose_name_plural = "Promotion Histories"
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['employee', 'end_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')) | models.Q(end_date__isnull=True),
                name='promotion_end_date_gte_start_date'
            ),
            models.UniqueConstraint(
                fields=['employee'],
                condition=models.Q(end_date__isnull=True),
                name='unique_active_promotion'
            ),
        ]

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new:
            # Validate start_date
            if self.start_date > date.today():
                logger.error(
                    f"New promotion start_date {self.start_date} is in the future for employee {self.employee_id}")
                raise ValidationError("Promotion start date cannot be in the future.")
            if self.start_date < self.employee.emp_joining_date:
                logger.error(
                    f"New promotion start_date {self.start_date} is before joining date {self.employee.emp_joining_date} for employee {self.employee_id}")
                raise ValidationError("Promotion start date cannot be before the employee's joining date.")

            # Close all previous active promotions
            previous_promotions = PromotionHistory.objects.select_for_update().filter(
                employee_id=self.employee_id,
                end_date__isnull=True,
                status='active'
            )
            for promotion in previous_promotions:
                new_end_date = self.start_date - timedelta(
                    days=1) if self.start_date > promotion.start_date else promotion.start_date
                promotion.end_date = new_end_date
                promotion.status = 'inactive'
                promotion.full_clean()  # Validate before saving
                promotion.save()
                logger.info(
                    f"Closed previous promotion {promotion.id} for employee {self.employee.id} with end_date {new_end_date}")

        self.full_clean()
        super().save(*args, **kwargs)

        if is_new:
            # Update Employee's current details
            self.employee.emp_department = self.department
            self.employee.emp_sub_department = self.sub_department
            self.employee.emp_category = self.category
            self.employee.emp_designation = self.designation
            self.employee.save()
            logger.info(f"Updated employee {self.employee.id} with new promotion details")
