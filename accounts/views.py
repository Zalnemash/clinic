from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import date
import json
import datetime

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
    if request.method == "POST":
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

        from .models import PatientProfile
        PatientProfile.objects.create(
            user=user,
            phone_number=phone,
            gender=gender
        )

        return JsonResponse({"message": "Patient registered successfully!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ---------------------------------------------------
# USER LOGIN
# ---------------------------------------------------
@csrf_exempt
def login_user(request):
    if request.method == "POST":
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

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ---------------------------------------------------
# DOCTOR REGISTRATION
# ---------------------------------------------------
@csrf_exempt
def register_doctor(request):
    if request.method == "POST":
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

        from .models import DoctorProfile
        DoctorProfile.objects.create(
            user=user,
            specialty=specialty,
            clinic_room=clinic_room,
            bio=bio
        )

        return JsonResponse({"message": "Doctor registered successfully!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ---------------------------------------------------
# ADD DOCTOR AVAILABILITY
# ---------------------------------------------------
@csrf_exempt
def add_availability(request):
    if request.method == "POST":
        data = json.loads(request.body)

        username = data.get("username")
        weekday = data.get("weekday")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        try:
            user = User.objects.get(username=username, role="DOCTOR")
            doctor_profile = user.doctor_profile
        except User.DoesNotExist:
            return JsonResponse({"error": "Doctor not found"}, status=404)

        from .models import Availability
        Availability.objects.create(
            doctor=doctor_profile,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time
        )

        return JsonResponse({"message": "Availability added!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ---------------------------------------------------
# BOOK APPOINTMENT  (FIXED — one csrf_exempt only)
# ---------------------------------------------------
@csrf_exempt
def book_appointment(request):
    if request.method == "POST":
        data = json.loads(request.body)

        patient_username = data.get("patient")
        doctor_username = data.get("doctor")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        # Convert ISO strings → datetime objects
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)

        weekday = start_dt.strftime("%A")

        # Get patient
        try:
            patient = User.objects.get(username=patient_username, role="PATIENT").patient_profile
        except User.DoesNotExist:
            return JsonResponse({"error": "Patient not found"}, status=404)

        # Get doctor
        try:
            doctor = User.objects.get(username=doctor_username, role="DOCTOR").doctor_profile
        except User.DoesNotExist:
            return JsonResponse({"error": "Doctor not found"}, status=404)

        from .models import Appointment, Availability

        # A) Check doctor availability
        availability = Availability.objects.filter(doctor=doctor, weekday=weekday).first()

        if not availability:
            return JsonResponse({"error": f"Doctor not available on {weekday}"}, status=400)

        avail_start = datetime.datetime.combine(start_dt.date(), availability.start_time)
        avail_end = datetime.datetime.combine(start_dt.date(), availability.end_time)

        if not (avail_start <= start_dt and end_dt <= avail_end):
            return JsonResponse({
                "error": f"Appointment outside availability ({availability.start_time}–{availability.end_time})"
            }, status=400)

        # B) Check overlapping appointments
        overlapping = Appointment.objects.filter(
            doctor=doctor,
            start_time__lt=end_dt,
            end_time__gt=start_dt
        ).exists()

        if overlapping:
            return JsonResponse({"error": "Doctor already has an appointment at this time"}, status=400)

        # C) Create appointment
        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            start_time=start_dt,
            end_time=end_dt,
            status="PENDING"
        )

        return JsonResponse({"message": "Appointment booked successfully!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ---------------------------------------------------
# UPDATE APPOINTMENT STATUS
# ---------------------------------------------------
@csrf_exempt
def update_appointment_status(request):
    if request.method == "POST":
        data = json.loads(request.body)

        appointment_id = data.get("appointment_id")
        new_status = data.get("status")

        from .models import Appointment

        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return JsonResponse({"error": "Appointment not found"}, status=404)

        appointment.status = new_status
        appointment.save()

        return JsonResponse({"message": "Appointment status updated!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ---------------------------------------------------
# PATIENT APPOINTMENTS LIST
# ---------------------------------------------------
def patient_appointments(request, username):
    try:
        user = User.objects.get(username=username, role="PATIENT")
        patient_profile = user.patient_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)

    appointments = patient_profile.appointments.all().order_by("start_time")

    data = [
        {
            "id": a.id,
            "doctor": a.doctor.user.username,
            "start_time": a.start_time,
            "end_time": a.end_time,
            "status": a.status
        }
        for a in appointments
    ]

    return JsonResponse({"appointments": data})


# ---------------------------------------------------
# DOCTOR DASHBOARD — ALL APPOINTMENTS
# ---------------------------------------------------
@csrf_exempt
def doctor_all_appointments(request, username):
    try:
        user = User.objects.get(username=username, role="DOCTOR")
        doctor_profile = user.doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    appointments = doctor_profile.appointments.all().order_by("start_time")

    data = [
        {
            "id": a.id,
            "patient": a.patient.user.username,
            "start_time": a.start_time,
            "end_time": a.end_time,
            "status": a.status
        }
        for a in appointments
    ]

    return JsonResponse({"appointments": data})


# ---------------------------------------------------
# DOCTOR DASHBOARD — PENDING ONLY
# ---------------------------------------------------
@csrf_exempt
def doctor_pending_appointments(request, username):
    try:
        user = User.objects.get(username=username, role="DOCTOR")
        doctor_profile = user.doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    appointments = doctor_profile.appointments.filter(status="PENDING")

    data = [
        {
            "id": a.id,
            "patient": a.patient.user.username,
            "start_time": a.start_time,
            "end_time": a.end_time,
            "status": a.status
        }
        for a in appointments
    ]

    return JsonResponse({"appointments": data})


# ---------------------------------------------------
# DOCTOR DASHBOARD — TODAY ONLY
# ---------------------------------------------------
@csrf_exempt
def doctor_today_appointments(request, username):
    try:
        user = User.objects.get(username=username, role="DOCTOR")
        doctor_profile = user.doctor_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    today = date.today()

    appointments = doctor_profile.appointments.filter(
        start_time__date=today
    ).order_by("start_time")

    data = [
        {
            "id": a.id,
            "patient": a.patient.user.username,
            "start_time": a.start_time,
            "end_time": a.end_time,
            "status": a.status
        }
        for a in appointments
    ]

    return JsonResponse({"appointments": data})


# ---------------------------------------------------
# MARK APPOINTMENT COMPLETED
# ---------------------------------------------------
@csrf_exempt
def doctor_complete_appointment(request):
    if request.method == "POST":
        data = json.loads(request.body)

        appointment_id = data.get("appointment_id")

        from .models import Appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return JsonResponse({"error": "Appointment not found"}, status=404)

        appointment.status = "COMPLETED"
        appointment.save()

        return JsonResponse({"message": "Appointment marked as completed!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)