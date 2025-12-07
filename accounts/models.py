from django.db import models
from django.contrib.auth.models import AbstractUser


# ---------------------------------
# Custom User Model
# ---------------------------------
class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('DOCTOR', 'Doctor'),
        ('PATIENT', 'Patient'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')

    def __str__(self):
        return f"{self.username} ({self.role})"


# ---------------------------------
# Doctor Profile
# ---------------------------------
class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    clinic_room = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Dr. {self.user.username} - {self.specialty}"


# ---------------------------------
# Patient Profile
# ---------------------------------
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"{self.user.username} (Patient)"


# ---------------------------------
# Doctor Availability (Kuwait week: Sunday = 0)
# ---------------------------------
class Availability(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='availabilities')
    weekday = models.IntegerField(choices=[
        (0, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.doctor.user.username} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


# ---------------------------------
# Appointment Model
# ---------------------------------
class Appointment(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.patient.user.username} → Dr. {self.doctor.user.username} at {self.start_time} ({self.status})"