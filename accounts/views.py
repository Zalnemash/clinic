from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import date
import json
import datetime

from .models import (
    PatientProfile,
    DoctorProfile,
    Appointment,
    Availability,
    MedicalReport
)

User = get_user_model()


# ---------------------------------------------------
# TEST FUNCTION
# ---------------------------------------------------
def test_api(request):
    return JsonResponse({"message": "API is working!"})


# ---------------------------------------------------
# PATIENT REGISTRATION
# ---------------------------------------------------
@csrf_exempt
def register_patient(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    username = data.get("username")
    password = data.get("password")
    phone = data.get("phone")
    gender = data.get("gender")

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

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

    return JsonResponse({"message": "Patient registered successfully!"})


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------
@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)
    username = data.get("username")
    password = data.get("password")

    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)

    if user is None:
        return JsonResponse({"error": "Invalid username or password"}, status=400)

    return JsonResponse({
        "message": "Login successful",
        "username": user.username,
        "role": user.role
    })


# ---------------------------------------------------
# DOCTOR REGISTRATION
# ---------------------------------------------------
@csrf_exempt
def register_doctor(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    username = data.get("username")
    password = data.get("password")
    specialty = data.get("specialty")
    clinic_room = data.get("clinic_room")
    bio = data.get("bio")

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

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

    return JsonResponse({"message": "Doctor registered successfully!"})


# ---------------------------------------------------
# ADD DOCTOR AVAILABILITY
# ---------------------------------------------------
@csrf_exempt
def add_availability(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    username = data.get("username")
    weekday = data.get("weekday")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    try:
        doctor = User.objects.get(username=username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    Availability.objects.create(
        doctor=doctor,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time
    )

    return JsonResponse({"message": "Availability added!"})


# ---------------------------------------------------
# BOOK APPOINTMENT (with validation)
# ---------------------------------------------------
@csrf_exempt
def book_appointment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    patient_username = data.get("patient")
    doctor_username = data.get("doctor")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    start_dt = datetime.datetime.fromisoformat(start_time)
    end_dt = datetime.datetime.fromisoformat(end_time)
    weekday = start_dt.weekday()

    # Patient
    try:
        patient = User.objects.get(username=patient_username, role="PATIENT").patient_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)

    # Doctor
    try:
        doctor = User.objects.get(username=doctor_username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    # A) Check availability
    availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()

    if not availability:
        return JsonResponse({"error": "Doctor not available this day"}, status=400)

    avail_start = datetime.datetime.combine(start_dt.date(), availability.start_time)
    avail_end = datetime.datetime.combine(start_dt.date(), availability.end_time)

    if not (avail_start <= start_dt and end_dt <= avail_end):
        return JsonResponse({"error": "Time outside doctor's availability"}, status=400)

    # B) Prevent overlaps
    overlap = Appointment.objects.filter(
        doctor=doctor,
        start_time__lt=end_dt,
        end_time__gt=start_dt
    ).exists()

    if overlap:
        return JsonResponse({"error": "Doctor already has an appointment in this slot"}, status=400)

    Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        start_time=start_dt,
        end_time=end_dt,
        status="PENDING"
    )

    return JsonResponse({"message": "Appointment booked successfully!"})


# ---------------------------------------------------
# UPDATE APPOINTMENT STATUS
# ---------------------------------------------------
@csrf_exempt
def update_appointment_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)
    appointment_id = data.get("appointment_id")
    new_status = data.get("status")

    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)

    appointment.status = new_status
    appointment.save()

    return JsonResponse({"message": "Appointment status updated"})


# ---------------------------------------------------
# PATIENT APPOINTMENTS
# ---------------------------------------------------
def patient_appointments(request, username):
    try:
        patient = User.objects.get(username=username, role="PATIENT").patient_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)

    appointments = patient.appointments.all().order_by("start_time")

    return JsonResponse({
        "appointments": [
            {
                "id": a.id,
                "doctor": a.doctor.user.username,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "status": a.status
            }
            for a in appointments
        ]
    })


# ---------------------------------------------------
# DOCTOR: ALL APPOINTMENTS
# ---------------------------------------------------
def doctor_all_appointments(request, username):
    try:
        doctor = User.objects.get(username=username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    appointments = doctor.appointments.all().order_by("start_time")

    return JsonResponse({
        "appointments": [
            {
                "id": a.id,
                "patient": a.patient.user.username,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "status": a.status
            }
            for a in appointments
        ]
    })


# ---------------------------------------------------
# DOCTOR: PENDING APPOINTMENTS
# ---------------------------------------------------
def doctor_pending_appointments(request, username):
    try:
        doctor = User.objects.get(username=username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    appointments = doctor.appointments.filter(status="PENDING")

    return JsonResponse({
        "appointments": [
            {
                "id": a.id,
                "patient": a.patient.user.username,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "status": a.status
            }
            for a in appointments
        ]
    })


# ---------------------------------------------------
# DOCTOR: TODAY'S APPOINTMENTS
# ---------------------------------------------------
def doctor_today_appointments(request, username):
    try:
        doctor = User.objects.get(username=username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    today = date.today()
    appointments = doctor.appointments.filter(start_time__date=today)

    return JsonResponse({
        "appointments": [
            {
                "id": a.id,
                "patient": a.patient.user.username,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "status": a.status
            }
            for a in appointments
        ]
    })


# ---------------------------------------------------
# CREATE MEDICAL REPORT
# ---------------------------------------------------
@csrf_exempt
def create_medical_report(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    appointment_id = data.get("appointment_id")
    diagnosis = data.get("diagnosis")
    prescription = data.get("prescription")
    notes = data.get("notes")

    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)

    if hasattr(appointment, "report"):
        return JsonResponse({"error": "Report already exists"}, status=400)

    report = MedicalReport.objects.create(
        appointment=appointment,
        diagnosis=diagnosis,
        prescription=prescription,
        notes=notes
    )

    return JsonResponse({
        "message": "Medical report created!",
        "report_id": report.id
    })


# ---------------------------------------------------
# GET MEDICAL REPORT
# ---------------------------------------------------
def get_medical_report(request, appointment_id):
    try:
        report = MedicalReport.objects.get(appointment_id=appointment_id)
    except MedicalReport.DoesNotExist:
        return JsonResponse({"error": "Report not found"}, status=404)

    appointment = report.appointment

    return JsonResponse({
        "appointment_id": appointment_id,
        "doctor": appointment.doctor.user.username,
        "patient": appointment.patient.user.username,
        "diagnosis": report.diagnosis,
        "prescription": report.prescription,
        "notes": report.notes,
        "created_at": report.created_at
    })


# ---------------------------------------------------
# UPDATE MEDICAL REPORT
# ---------------------------------------------------
@csrf_exempt
def update_medical_report(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    report_id = data.get("report_id")

    try:
        report = MedicalReport.objects.get(id=report_id)
    except MedicalReport.DoesNotExist:
        return JsonResponse({"error": "Report not found"}, status=404)

    report.diagnosis = data.get("diagnosis", report.diagnosis)
    report.prescription = data.get("prescription", report.prescription)
    report.notes = data.get("notes", report.notes)
    report.save()

    return JsonResponse({"message": "Medical report updated successfully!"})