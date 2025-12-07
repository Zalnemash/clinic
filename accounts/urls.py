from django.urls import path
from . import views

urlpatterns = [
    path("test/", views.test_api),

    # Authentication
    path("register/patient/", views.register_patient),
    path("login/", views.login_user),
    path("register/doctor/", views.register_doctor),

    # Doctor availability
    path("doctor/add-availability/", views.add_availability, name="add_availability"),

    # Appointment actions
    path("book/", views.book_appointment, name="book_appointment"),
    path("appointment/update/", views.update_appointment_status),

    # Patient appointments
    path("patient/<str:username>/appointments/", views.patient_appointments),

    # Doctor Dashboard (ORDER MATTERS)
    path("doctor/<str:username>/appointments/pending/", views.doctor_pending_appointments),
    path("doctor/<str:username>/appointments/today/", views.doctor_today_appointments),

    # Must be LAST because it's the general pattern
    path("doctor/<str:username>/appointments/", views.doctor_all_appointments),

    # Doctor marks appointment completed
    path("doctor/appointment/complete/", views.doctor_complete_appointment),
]