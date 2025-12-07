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
# DOCTOR: ALL APPOINTMENTS
# ---------------------------------------------------
@api_view(['GET'])
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
# DOCTOR: PENDING APPOINTMENTS
# ---------------------------------------------------
@api_view(['GET'])
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
# DOCTOR: TODAY'S APPOINTMENTS
# ---------------------------------------------------
@api_view(['GET'])
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
# DOCTOR CALENDAR (Available Slots for Given Date)
# ---------------------------------------------------
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def doctor_calendar(request, username):

    try:
        doctor = User.objects.get(username=username, role="DOCTOR").doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"error": "Missing 'date' (YYYY-MM-DD)"}, status=400)

    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    weekday = date_obj.weekday()

    availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()
    if not availability:
        return JsonResponse({"available_slots": []})

    start_dt = datetime.datetime.combine(date_obj, availability.start_time)
    end_dt = datetime.datetime.combine(date_obj, availability.end_time)

    taken = Appointment.objects.filter(
        doctor=doctor,
        start_time__date=date_obj
    )

    taken_slots = [(a.start_time, a.end_time) for a in taken]

    slots = []
    current = start_dt
    while current < end_dt:
        slot_end = current + datetime.timedelta(minutes=30)

        conflict = any(
            t_start < slot_end and t_end > current
            for t_start, t_end in taken_slots
        )

        if not conflict:
            slots.append({
                "start": current.isoformat(),
                "end": slot_end.isoformat()
            })

        current = slot_end

    return JsonResponse({"available_slots": slots})


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