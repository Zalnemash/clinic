from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
import json

User = get_user_model()


# --------------------------
# TEST FUNCTION
# --------------------------
def test_api(request):
    return JsonResponse({"message": "API is working!"})


# --------------------------
# PATIENT REGISTRATION API
# --------------------------
@csrf_exempt
def register_patient(request):
    if request.method == "POST":
        data = json.loads(request.body)

        username = data.get("username")
        password = data.get("password")
        phone = data.get("phone")
        gender = data.get("gender")

        # Check if username exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)

        # Create USER with PATIENT role
        user = User.objects.create_user(
            username=username,
            password=password,
            role="PATIENT"
        )

        # Create patient profile
        from .models import PatientProfile
        PatientProfile.objects.create(
            user=user,
            phone_number=phone,
            gender=gender
        )

        return JsonResponse({"message": "Patient registered successfully!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)
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
@csrf_exempt
def register_doctor(request):
    if request.method == "POST":
        data = json.loads(request.body)

        username = data.get("username")
        password = data.get("password")
        specialty = data.get("specialty")
        clinic_room = data.get("clinic_room")
        bio = data.get("bio")

        # Check if username exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)

        # Create the doctor user
        user = User.objects.create_user(
            username=username,
            password=password,
            role="DOCTOR"
        )

        # Create doctor profile
        from .models import DoctorProfile
        DoctorProfile.objects.create(
            user=user,
            specialty=specialty,
            clinic_room=clinic_room,
            bio=bio
        )

        return JsonResponse({"message": "Doctor registered successfully!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)
@csrf_exempt
def add_availability(request):
    if request.method == "POST":
        data = json.loads(request.body)

        username = data.get("username")  # doctor username
        weekday = data.get("weekday")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        # Get doctor user
        try:
            user = User.objects.get(username=username, role="DOCTOR")
        except User.DoesNotExist:
            return JsonResponse({"error": "Doctor not found"}, status=404)

        doctor_profile = user.doctor_profile

        # Create availability
        from .models import Availability
        Availability.objects.create(
            doctor=doctor_profile,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time
        )

        return JsonResponse({"message": "Availability added!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)
@csrf_exempt
def book_appointment(request):
    if request.method == "POST":
        data = json.loads(request.body)

        patient_username = data.get("patient")
        doctor_username = data.get("doctor")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        # Get patient
        try:
            patient_user = User.objects.get(username=patient_username, role="PATIENT")
            patient_profile = patient_user.patient_profile
        except User.DoesNotExist:
            return JsonResponse({"error": "Patient not found"}, status=404)

        # Get doctor
        try:
            doctor_user = User.objects.get(username=doctor_username, role="DOCTOR")
            doctor_profile = doctor_user.doctor_profile
        except User.DoesNotExist:
            return JsonResponse({"error": "Doctor not found"}, status=404)

        # Create appointment
        from .models import Appointment
        Appointment.objects.create(
            patient=patient_profile,
            doctor=doctor_profile,
            start_time=start_time,
            end_time=end_time,
            status="PENDING"
        )

        return JsonResponse({"message": "Appointment booked!"})

    return JsonResponse({"error": "Invalid request method"}, status=400)
@csrf_exempt
def update_appointment_status(request):
    if request.method == "POST":
        data = json.loads(request.body)

        appointment_id = data.get("appointment_id")
        new_status = data.get("status")  # CONFIRMED, CANCELLED, COMPLETED

        from .models import Appointment

        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return JsonResponse({"error": "Appointment not found"}, status=404)

        # Update status
        appointment.status = new_status
        appointment.save()

        return JsonResponse({
            "message": "Appointment status updated!",
            "appointment": str(appointment)
        })

    return JsonResponse({"error": "Invalid request method"}, status=400)
def patient_appointments(request, username):
    try:
        user = User.objects.get(username=username, role="PATIENT")
        patient_profile = user.patient_profile
    except User.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)

    appointments = patient_profile.appointments.all().order_by("start_time")

    data = [
        {
            "doctor": a.doctor.user.username,
            "start_time": a.start_time,
            "end_time": a.end_time,
            "status": a.status
        }
        for a in appointments
    ]

    return JsonResponse({"appointments": data})