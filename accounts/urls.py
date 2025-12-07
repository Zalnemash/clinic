from django.urls import path
from . import views

urlpatterns = [
    path("test/", views.test_api),

    # Authentication
    path("register/patient/", views.register_patient),
    path("login/", views.login_user),
    path("register/doctor/", views.register_doctor),

    # Availability
    path("doctor/add-availability/", views.add_availability),

    # Appointments
    path("book/", views.book_appointment),
    path("appointment/update/", views.update_appointment_status),

    # Medical Reports
    path("report/create/", views.create_medical_report),
    path("report/<int:appointment_id>/", views.get_medical_report),

    # Patient dashboard
    path("patient/<str:username>/appointments/", views.patient_appointments),

    # Doctor dashboard (order matters)
    path("doctor/<str:username>/appointments/pending/", views.doctor_pending_appointments),
    path("doctor/<str:username>/appointments/today/", views.doctor_today_appointments),
    path("doctor/<str:username>/appointments/", views.doctor_all_appointments),
]