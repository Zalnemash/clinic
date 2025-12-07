from django.urls import path
from . import views

urlpatterns = [
    path("test/", views.test_api),
    path("register/patient/", views.register_patient),
    path("login/", views.login_user),
    path("register/doctor/", views.register_doctor),
    path("doctor/add-availability/", views.add_availability, name="add_availability"),
    path("book/", views.book_appointment, name="book_appointment"),
    path("appointment/update/", views.update_appointment_status),
    path("patient/<str:username>/appointments/", views.patient_appointments),
]