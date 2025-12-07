from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from datetime import date
import datetime
import json

# DRF + JWT
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import (
    PatientProfile,
    DoctorProfile,
    Appointment,
    Availability,
    MedicalReport
)

User = get_user_model()


# ---------------------------------------------------
# TEST
# ---------------------------------------------------
def test_api(request):
    return JsonResponse({"message": "API is working!"})


# ---------------------------------------------------
# PATIENT REGISTRATION  (PUBLIC)
# ---------------------------------------------------
@csrf_exempt
def register_patient(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)

    username = data.get("username")
    password = data.get("password")
    phone = data.get("phone")
    gender = data.get("gender")

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

    user = User.objects.create_user(username=username, password=password, role="PATIENT")
    PatientProfile.objects.create(user=user, phone_number=phone, gender=gender)

    return JsonResponse({"message": "Patient registered successfully!"})


# ---------------------------------------------------
# DOCTOR REGISTRATION (PUBLIC)
# ---------------------------------------------------
@csrf_exempt
def register_doctor(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)

    username = data.get("username")
    password = data.get("password")
    specialty = data.get("specialty")
    clinic_room = data.get("clinic_room")
    bio = data.get("bio")

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

    user = User.objects.create_user(username=username, password=password, role="DOCTOR")
    DoctorProfile.objects.create(
        user=user,
        specialty=specialty,
        clinic_room=clinic_room,
        bio=bio
    )

    return JsonResponse({"message": "Doctor registered successfully!"})


# ---------------------------------------------------
# LOGIN (PUBLIC)
# ---------------------------------------------------
@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)
    username = data.get("username")
    password = data.get("password")

    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)

    if not user:
        return JsonResponse({"error": "Invalid credentials"}, status=400)

    return JsonResponse({"message": "Login successful", "role": user.role})


# ---------------------------------------------------
# ADD DOCTOR AVAILABILITY  (DOCTOR ONLY)
# ---------------------------------------------------
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def add_availability(request):

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can add availability"}, status=403)

    data = request.data

    Availability.objects.create(
        doctor=request.user.doctor_profile,
        weekday=data.get("weekday"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time")
    )

    return JsonResponse({"message": "Availability added!"})


# ---------------------------------------------------
# BOOK APPOINTMENT (PATIENT ONLY)
# ---------------------------------------------------
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def book_appointment(request):

    if request.user.role != "PATIENT":
        return JsonResponse({"error": "Only patients can book"}, status=403)

    data = request.data
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

    availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()
    if not availability:
        return JsonResponse({"error": "Doctor not available on this day"}, status=400)

    avail_start = datetime.datetime.combine(start_dt.date(), availability.start_time)
    avail_end = datetime.datetime.combine(start_dt.date(), availability.end_time)

    if start_dt < avail_start or end_dt > avail_end:
        return JsonResponse({"error": "Time outside doctor's availability"}, status=400)

    overlap = Appointment.objects.filter(
        doctor=doctor,
        start_time__lt=end_dt,
        end_time__gt=start_dt
    ).exists()
    if overlap:
        return JsonResponse({"error": "This time is already booked"}, status=400)

    Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        start_time=start_dt,
        end_time=end_dt
    )

    return JsonResponse({"message": "Appointment booked!"})


# ---------------------------------------------------
# UPDATE APPOINTMENT STATUS (DOCTOR ONLY)
# ---------------------------------------------------
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_appointment_status(request):

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can update status"}, status=403)

    data = request.data
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
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if not hasattr(request.user, "role") or request.user.role != "PATIENT":
        return JsonResponse({"error": "Only patients can view their appointments"}, status=403)

    if request.user.username != username:
        return JsonResponse({"error": "Forbidden"}, status=403)

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
# CREATE MEDICAL REPORT (DOCTOR ONLY)
# ---------------------------------------------------
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_medical_report(request):

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can create reports"}, status=403)

    data = request.data
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

    return JsonResponse({"message": "Report created", "report_id": report.id})


# ---------------------------------------------------
# GET MEDICAL REPORT (Doctor or Patient)
# ---------------------------------------------------
@api_view(['GET'])
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
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_medical_report(request):

    if request.user.role != "DOCTOR":
        return JsonResponse({"error": "Only doctors can update reports"}, status=403)

    data = request.data
    report_id = data.get("report_id")

    try:
        report = MedicalReport.objects.get(id=report_id, appointment__doctor=request.user.doctor_profile)
    except MedicalReport.DoesNotExist:
        return JsonResponse({"error": "Report not found or unauthorized"}, status=404)

    report.diagnosis = data.get("diagnosis", report.diagnosis)
    report.prescription = data.get("prescription", report.prescription)
    report.notes = data.get("notes", report.notes)
    report.save()

    return JsonResponse({"message": "Report updated!"})