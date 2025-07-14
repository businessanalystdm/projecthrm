from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from hr.models import Branches

class MobilePunchin(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # Stores hashed password
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_password(self, raw_password):
        """
        Hash the password before saving.
        """
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """
        Verify the password against the stored hash.
        """
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        db_table = 'mobile_punchin'
        verbose_name = 'Mobile Punch-in'
        verbose_name_plural = 'Mobile Punch-ins'

class PunchRecord(models.Model):
    user = models.ForeignKey(
        MobilePunchin,
        on_delete=models.CASCADE,
        related_name='punch_records'
    )
    date = models.DateField(default=timezone.now)
    punch_in_time = models.DateTimeField(null=True, blank=True)
    punch_in_branch=models.ForeignKey(Branches, on_delete=models.CASCADE, related_name='punch_in_branches')
    punch_out_time = models.DateTimeField(null=True, blank=True)
    punch_out_branch=models.ForeignKey(Branches, on_delete=models.CASCADE, related_name='punch_out_branches',null=True, blank=True)

    def __str__(self):
        return f"Punch record for {self.user.username} on {self.date}"

    class Meta:
        db_table = 'punch_record'
        verbose_name = 'Punch Record'
        verbose_name_plural = 'Punch Records'
        unique_together = ('user', 'date')


