from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import date
import json
import datetime

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

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
# PATIENT REGISTRATION  (No JWT required)
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
# LOGIN (No JWT required)
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
# DOCTOR REGISTRATION (No JWT required)
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
# ADD DOCTOR AVAILABILITY  (DOCTOR ONLY - JWT Protected)
# ---------------------------------------------------
@csrf_exempt
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def add_availability(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can add availability"}, status=403)

    data = json.loads(request.body)

    weekday = data.get("weekday")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    doctor = request.user.doctor_profile

    Availability.objects.create(
        doctor=doctor,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time
    )

    return JsonResponse({"message": "Availability added!"})


# ---------------------------------------------------
# BOOK APPOINTMENT (PATIENT ONLY - JWT Protected)
# ---------------------------------------------------
@csrf_exempt
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def book_appointment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    if request.user.role != "PATIENT":
        return JsonResponse({"error": "Only patients can book appointments"}, status=403)

    data = json.loads(request.body)

    doctor_username = data.get("doctor")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    start_dt = datetime.datetime.fromisoformat(start_time)
    end_dt = datetime.datetime.fromisoformat(end_time)
    weekday = start_dt.weekday()

    patient = request.user.patient_profile

    try:
        doctor = User.objects.get(username=doctor_username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    # Check availability
    availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()
    if not availability:
        return JsonResponse({"error": "Doctor not available this day"}, status=400)

    # Check time window
    avail_start = datetime.datetime.combine(start_dt.date(), availability.start_time)
    avail_end = datetime.datetime.combine(start_dt.date(), availability.end_time)
    if not (avail_start <= start_dt <= avail_end and end_dt <= avail_end):
        return JsonResponse({"error": "Time outside doctor's availability"}, status=400)

    # Check overlap
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
# UPDATE APPOINTMENT STATUS (DOCTOR ONLY - JWT Protected)
# ---------------------------------------------------
@csrf_exempt
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_appointment_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can update status"}, status=403)

    data = json.loads(request.body)
    appointment_id = data.get("appointment_id")
    new_status = data.get("status")

    try:
        appointment = Appointment.objects.get(id=appointment_id, doctor=request.user.doctor_profile)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)

    appointment.status = new_status
    appointment.save()

    return JsonResponse({"message": "Status updated"})


# ---------------------------------------------------
# PATIENT APPOINTMENTS (JWT Protected)
# ---------------------------------------------------
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def patient_appointments(request, username):
    if request.user.role != "PATIENT" or request.user.username != username:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    patient = request.user.patient_profile
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
# DOCTOR: ALL APPOINTMENTS (JWT Protected)
# ---------------------------------------------------
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def doctor_all_appointments(request, username):
    if request.user.role != "DOCTOR" or request.user.username != username:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    doctor = request.user.doctor_profile
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
# DOCTOR: PENDING APPOINTMENTS (JWT Protected)
# ---------------------------------------------------
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def doctor_pending_appointments(request, username):
    if request.user.role != "DOCTOR" or request.user.username != username:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    doctor = request.user.doctor_profile
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
# DOCTOR: TODAY'S APPOINTMENTS (JWT Protected)
# ---------------------------------------------------
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def doctor_today_appointments(request, username):
    if request.user.role != "DOCTOR" or request.user.username != username:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    doctor = request.user.doctor_profile
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
# CREATE MEDICAL REPORT (DOCTOR ONLY - JWT Protected)
# ---------------------------------------------------
@csrf_exempt
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_medical_report(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can create reports"}, status=403)

    data = json.loads(request.body)
    appointment_id = data.get("appointment_id")

    try:
        appointment = Appointment.objects.get(id=appointment_id, doctor=request.user.doctor_profile)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)

    if hasattr(appointment, "report"):
        return JsonResponse({"error": "Report already exists"}, status=400)

    report = MedicalReport.objects.create(
        appointment=appointment,
        diagnosis=data.get("diagnosis"),
        prescription=data.get("prescription"),
        notes=data.get("notes")
    )

    return JsonResponse({"message": "Medical report created!", "report_id": report.id})


# ---------------------------------------------------
# GET MEDICAL REPORT (Only patient OR doctor - JWT Protected)
# ---------------------------------------------------
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_medical_report(request, appointment_id):

    try:
        report = MedicalReport.objects.get(appointment_id=appointment_id)
    except MedicalReport.DoesNotExist:
        return JsonResponse({"error": "Report not found"}, status=404)

    appointment = report.appointment

    # Access rules
    if request.user.role == "PATIENT" and request.user != appointment.patient.user:
        return JsonResponse({"error": "Not allowed"}, status=403)

    if request.user.role == "DOCTOR" and request.user != appointment.doctor.user:
        return JsonResponse({"error": "Not allowed"}, status=403)

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
# UPDATE MEDICAL REPORT (DOCTOR ONLY)
# ---------------------------------------------------
@csrf_exempt
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_medical_report(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can update reports"}, status=403)

    data = json.loads(request.body)
    report_id = data.get("report_id")

    try:
        report = MedicalReport.objects.get(id=report_id, appointment__doctor=request.user.doctor_profile)
    except MedicalReport.DoesNotExist:
        return JsonResponse({"error": "Report not found"}, status=404)

    report.diagnosis = data.get("diagnosis", report.diagnosis)
    report.prescription = data.get("prescription", report.prescription)
    report.notes = data.get("notes", report.notes)
    report.save()

    return JsonResponse({"message": "Medical report updated successfully!"})