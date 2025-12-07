from django.contrib import admin
from .models import User, PatientProfile, DoctorProfile, Appointment, Availability, MedicalReport

admin.site.register(User)
admin.site.register(PatientProfile)
admin.site.register(DoctorProfile)
admin.site.register(Appointment)
admin.site.register(Availability)
admin.site.register(MedicalReport)