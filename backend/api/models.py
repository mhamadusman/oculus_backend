
from django.db import models  # Import models for database interaction
from django.contrib.auth.models import User 
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hospital = models.CharField(max_length=100, blank=True, null=True)
    specialty = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=100, default='general')
    license_number = models.CharField(max_length=50, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.IntegerField(blank=True , null=True)