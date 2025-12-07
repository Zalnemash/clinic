from django.urls import path
from . import views

urlpatterns = [
    path("test/", views.test_api),

    # Authentication
    path("register/patient/", views.register_patient),
    path("login/", views.login_user),
    path("register/doctor/", views.register_doctor),

    # Availability (Doctor)
    path("doctor/add-availability/", views.add_availability),

    # Appointments
    path("book/", views.book_appointment),
    path("appointment/update/", views.update_appointment_status),

    # Patient
    path("patient/<str:username>/appointments/", views.patient_appointments),

    # Medical Reports
    path("report/create/", views.create_medical_report),
    path("report/<int:appointment_id>/", views.get_medical_report),
    path("report/update/", views.update_medical_report),
]