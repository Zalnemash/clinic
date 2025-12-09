from datetime import date
import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    PatientProfile,
    DoctorProfile,
    Appointment,
    Availability,
    MedicalReport
)

User = get_user_model()


# ---------------------------------------------------
# HOME
# ---------------------------------------------------
def home_page(request):
    """
    Simple landing / dashboard.
    You can customize to show different content based on user role.
    """
    context = {}
    if request.user.is_authenticated:
        context["role"] = getattr(request.user, "role", None)
    return render(request, "accounts/home.html", context)


# ---------------------------------------------------
# AUTH VIEWS
# ---------------------------------------------------
def login_view(request):
    """
    Replaces login_user API.
    GET: show login form.
    POST: authenticate and log in, then redirect to home.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Invalid username or password.")
        else:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("home")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


def register_patient_view(request):
    """
    Replaces /register/patient/ API.
    GET: show registration form.
    POST: create User + PatientProfile, log in, redirect.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        phone = request.POST.get("phone")
        gender = request.POST.get("gender")

        if password != password2:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                role="PATIENT"
            )
            PatientProfile.objects.create(
                user=user,
                phone_number=phone,
                gender=gender
            )
            login(request, user)
            messages.success(request, "Patient account created and logged in.")
            return redirect("home")

    return render(request, "accounts/register_patient.html")


def register_doctor_view(request):
    """
    Replaces /register/doctor/ API.
    GET: show form.
    POST: create User + DoctorProfile.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        specialty = request.POST.get("specialty")
        clinic_room = request.POST.get("clinic_room")
        bio = request.POST.get("bio")

        if password != password2:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                role="DOCTOR"
            )
            DoctorProfile.objects.create(
                user=user,
                specialty=specialty,
                clinic_room=clinic_room,
                bio=bio
            )
            login(request, user)
            messages.success(request, "Doctor account created and logged in.")
            return redirect("home")

    return render(request, "accounts/register_doctor.html")


# ---------------------------------------------------
# DOCTOR AVAILABILITY
# ---------------------------------------------------
@login_required
def add_availability_view(request):
    """
    Replaces add_availability API.
    Only doctors can access.
    GET: show form.
    POST: create availability record.
    """
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Only doctors can add availability.")
        return redirect("home")

    if request.method == "POST":
        weekday = int(request.POST.get("weekday"))  # 0=Mon ... 6=Sun
        start_time_str = request.POST.get("start_time")  # "HH:MM"
        end_time_str = request.POST.get("end_time")

        try:
            start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
        except (TypeError, ValueError):
            messages.error(request, "Invalid time format.")
        else:
            Availability.objects.create(
                doctor=request.user.doctor_profile,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time
            )
            messages.success(request, "Availability added.")
            return redirect("add_availability")

    return render(request, "accounts/add_availability.html")


# ---------------------------------------------------
# DOCTOR CALENDAR – AVAILABLE SLOTS FOR GIVEN DATE
# ---------------------------------------------------
@login_required
def doctor_calendar_view(request, username):
    """
    Replaces doctor_calendar API.
    Shows a list of free 30-minute slots for a chosen date.
    """
    doctor_user = get_object_or_404(User, username=username, role="DOCTOR")
    doctor = doctor_user.doctor_profile

    # date passed as ?date=YYYY-MM-DD (default: today)
    date_str = request.GET.get("date")
    if not date_str:
        date_obj = date.today()
    else:
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format, using today.")
            date_obj = date.today()

    weekday = date_obj.weekday()
    availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()

    available_slots = []
    if availability:
        start_dt = datetime.datetime.combine(date_obj, availability.start_time)
        end_dt = datetime.datetime.combine(date_obj, availability.end_time)

        taken = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=date_obj
        )
        taken_slots = [(a.start_time, a.end_time) for a in taken]

        current = start_dt
        while current < end_dt:
            slot_end = current + datetime.timedelta(minutes=30)

            conflict = any(
                t_start < slot_end and t_end > current
                for t_start, t_end in taken_slots
            )

            if not conflict:
                available_slots.append(
                    {
                        "start": current,
                        "end": slot_end,
                    }
                )

            current = slot_end

    context = {
        "doctor": doctor,
        "date": date_obj,
        "available_slots": available_slots,
    }
    return render(request, "accounts/doctor_calendar.html", context)


# ---------------------------------------------------
# BOOK APPOINTMENT (PATIENT)
# ---------------------------------------------------
@login_required
def book_appointment_view(request):
    """
    Replaces book_appointment API.
    GET: show booking form.
    POST: validate slot and create Appointment.
    """
    if getattr(request.user, "role", None) != "PATIENT":
        messages.error(request, "Only patients can book appointments.")
        return redirect("home")

    doctors = DoctorProfile.objects.select_related("user").all()

    if request.method == "POST":
        doctor_username = request.POST.get("doctor")
        start_time_str = request.POST.get("start_time")  # ISO: "YYYY-MM-DDTHH:MM"
        end_time_str = request.POST.get("end_time")

        try:
            start_dt = datetime.datetime.fromisoformat(start_time_str)
            end_dt = datetime.datetime.fromisoformat(end_time_str)
        except (TypeError, ValueError):
            messages.error(request, "Invalid start or end time.")
            return render(request, "accounts/book_appointment.html", {"doctors": doctors})

        try:
            doctor_user = User.objects.get(username=doctor_username, role="DOCTOR")
            doctor = doctor_user.doctor_profile
        except User.DoesNotExist:
            messages.error(request, "Doctor not found.")
            return render(request, "accounts/book_appointment.html", {"doctors": doctors})

        weekday = start_dt.weekday()
        availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()
        if not availability:
            messages.error(request, "Doctor is not available on this day.")
            return render(request, "accounts/book_appointment.html", {"doctors": doctors})

        avail_start = datetime.datetime.combine(start_dt.date(), availability.start_time)
        avail_end = datetime.datetime.combine(start_dt.date(), availability.end_time)

        if start_dt < avail_start or end_dt > avail_end:
            messages.error(request, "Time is outside doctor's availability.")
            return render(request, "accounts/book_appointment.html", {"doctors": doctors})

        overlap = Appointment.objects.filter(
            doctor=doctor,
            start_time__lt=end_dt,
            end_time__gt=start_dt
        ).exists()
        if overlap:
            messages.error(request, "This time slot is already booked.")
            return render(request, "accounts/book_appointment.html", {"doctors": doctors})

        Appointment.objects.create(
            patient=request.user.patient_profile,
            doctor=doctor,
            start_time=start_dt,
            end_time=end_dt
        )
        messages.success(request, "Appointment booked successfully.")
        return redirect("patient_appointments")

    return render(request, "accounts/book_appointment.html", {"doctors": doctors})


# ---------------------------------------------------
# UPDATE APPOINTMENT STATUS (DOCTOR)
# ---------------------------------------------------
@login_required
def update_appointment_status_view(request, appointment_id):
    """
    Replaces update_appointment_status API.
    Doctor chooses new status via form (e.g. PENDING / CONFIRMED / CANCELED).
    """
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Only doctors can update appointment status.")
        return redirect("home")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=request.user.doctor_profile
    )

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status:
            appointment.status = new_status
            appointment.save()
            messages.success(request, "Appointment status updated.")
            return redirect("doctor_all_appointments")

    return render(request, "accounts/update_appointment_status.html", {"appointment": appointment})


# ---------------------------------------------------
# PATIENT APPOINTMENTS
# ---------------------------------------------------
@login_required
def patient_appointments_view(request):
    """
    Replaces patient_appointments API but uses logged-in user instead of URL username.
    """
    if getattr(request.user, "role", None) != "PATIENT":
        messages.error(request, "Unauthorized.")
        return redirect("home")

    patient = request.user.patient_profile
    appointments = patient.appointments.select_related("doctor__user").order_by("start_time")

    return render(request, "accounts/patient_appointments.html", {
        "appointments": appointments
    })


# ---------------------------------------------------
# DOCTOR APPOINTMENTS (ALL / PENDING / TODAY)
# ---------------------------------------------------
@login_required
def doctor_all_appointments_view(request):
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Unauthorized.")
        return redirect("home")

    doctor = request.user.doctor_profile
    appointments = doctor.appointments.select_related("patient__user").order_by("start_time")

    return render(request, "accounts/doctor_appointments.html", {
        "appointments": appointments
    })


@login_required
def doctor_pending_appointments_view(request):
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Unauthorized.")
        return redirect("home")

    doctor = request.user.doctor_profile
    appointments = doctor.appointments.select_related("patient__user").filter(status="PENDING")

    return render(request, "accounts/doctor_pending_appointments.html", {
        "appointments": appointments
    })


@login_required
def doctor_today_appointments_view(request):
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Unauthorized.")
        return redirect("home")

    doctor = request.user.doctor_profile
    today = date.today()
    appointments = doctor.appointments.select_related("patient__user").filter(
        start_time__date=today
    )

    return render(request, "accounts/doctor_today_appointments.html", {
        "appointments": appointments,
        "today": today,
    })


# ---------------------------------------------------
# UPCOMING APPOINTMENTS (REMINDERS)
# ---------------------------------------------------
@login_required
def upcoming_appointments_view(request):
    """
    Replaces upcoming_appointments API.
    Shows appointments in the next 24 hours for patient/doctor.
    """
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(hours=24)

    role = getattr(request.user, "role", None)

    if role == "PATIENT":
        appointments = Appointment.objects.filter(
            patient=request.user.patient_profile,
            start_time__gte=now,
            start_time__lte=tomorrow
        ).order_by("start_time")
    elif role == "DOCTOR":
        appointments = Appointment.objects.filter(
            doctor=request.user.doctor_profile,
            start_time__gte=now,
            start_time__lte=tomorrow
        ).order_by("start_time")
    else:
        messages.error(request, "Invalid role.")
        return redirect("home")

    return render(request, "accounts/upcoming_appointments.html", {
        "appointments": appointments,
        "now": now,
        "tomorrow": tomorrow,
    })


# ---------------------------------------------------
# MEDICAL REPORTS
# ---------------------------------------------------
@login_required
def create_medical_report_view(request, appointment_id):
    """
    Replaces create_medical_report API.
    Only doctor for that appointment can create the report.
    GET: show form.
    POST: create report.
    """
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Only doctors can create reports.")
        return redirect("home")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=request.user.doctor_profile
    )

    if hasattr(appointment, "report"):
        messages.error(request, "Report already exists for this appointment.")
        return redirect("get_medical_report", appointment_id=appointment_id)

    if request.method == "POST":
        diagnosis = request.POST.get("diagnosis")
        prescription = request.POST.get("prescription")
        notes = request.POST.get("notes")

        report = MedicalReport.objects.create(
            appointment=appointment,
            diagnosis=diagnosis,
            prescription=prescription,
            notes=notes
        )
        messages.success(request, "Report created.")
        return redirect("get_medical_report", appointment_id=appointment_id)

    return render(request, "accounts/create_medical_report.html", {
        "appointment": appointment
    })


from django.http import Http404

@login_required
def get_medical_report_view(request, appointment_id):
    # First get the appointment itself
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Permission check: only that doctor / patient
    role = getattr(request.user, "role", None)
    if role == "PATIENT" and request.user != appointment.patient.user:
        messages.error(request, "You are not allowed to view this report.")
        return redirect("home")
    if role == "DOCTOR" and request.user != appointment.doctor.user:
        messages.error(request, "You are not allowed to view this report.")
        return redirect("home")

    # Try to get report
    try:
        report = appointment.report
    except MedicalReport.DoesNotExist:
        # No report exists yet
        if role == "DOCTOR":
            messages.info(request, "No report exists for this appointment yet. Create one now.")
            return redirect("create_medical_report", appointment_id=appointment_id)
        else:
            messages.info(request, "No report has been created yet for this appointment.")
            return redirect("patient_appointments")

    # If report exists, render as usual
    return render(request, "accounts/medical_report.html", {
        "appointment": appointment,
        "report": report,
    })


@login_required
def update_medical_report_view(request, report_id):
    """
    Replaces update_medical_report API.
    Only the doctor of that appointment can edit.
    """
    if getattr(request.user, "role", None) != "DOCTOR":
        messages.error(request, "Only doctors can update reports.")
        return redirect("home")

    report = get_object_or_404(
        MedicalReport,
        id=report_id,
        appointment__doctor=request.user.doctor_profile
    )

    if request.method == "POST":
        report.diagnosis = request.POST.get("diagnosis", report.diagnosis)
        report.prescription = request.POST.get("prescription", report.prescription)
        report.notes = request.POST.get("notes", report.notes)
        report.save()
        messages.success(request, "Report updated.")
        return redirect("get_medical_report", appointment_id=report.appointment_id)

    return render(request, "accounts/update_medical_report.html", {
        "report": report,
        "appointment": report.appointment,
    })
