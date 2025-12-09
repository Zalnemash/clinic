from django.urls import path
from . import views

urlpatterns = [
    # Home
    path("", views.home_page, name="home"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/patient/", views.register_patient_view, name="register_patient"),
    path("register/doctor/", views.register_doctor_view, name="register_doctor"),

    # Doctor availability & calendar
    path("doctor/add-availability/", views.add_availability_view, name="add_availability"),
    path("doctor/<str:username>/calendar/", views.doctor_calendar_view, name="doctor_calendar"),

    # Appointments
    path("appointments/book/", views.book_appointment_view, name="book_appointment"),
    path("appointments/update-status/<int:appointment_id>/", views.update_appointment_status_view, name="update_appointment_status"),

    # Patient views
    path("patient/appointments/", views.patient_appointments_view, name="patient_appointments"),

    # Doctor appointment views
    path("doctor/appointments/", views.doctor_all_appointments_view, name="doctor_all_appointments"),
    path("doctor/appointments/pending/", views.doctor_pending_appointments_view, name="doctor_pending_appointments"),
    path("doctor/appointments/today/", views.doctor_today_appointments_view, name="doctor_today_appointments"),

    # Upcoming appointments (reminders)
    path("reminders/", views.upcoming_appointments_view, name="upcoming_appointments"),

    # Medical reports
    path("report/create/<int:appointment_id>/", views.create_medical_report_view, name="create_medical_report"),
    path("report/<int:appointment_id>/", views.get_medical_report_view, name="get_medical_report"),
    path("report/update/<int:report_id>/", views.update_medical_report_view, name="update_medical_report"),
]
