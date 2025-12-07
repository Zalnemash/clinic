from django.contrib import admin
from .models import User, DoctorProfile, PatientProfile, Availability, Appointment

admin.site.register(User)
admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)
admin.site.register(Availability)
admin.site.register(Appointment)