from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import MobilePunchin
import logging
from django.contrib.auth import authenticate, login


logger = logging.getLogger(__name__)

@csrf_exempt
def create_mobile_punchin_id(request):
    if request.method == 'POST':
        try:
            id = request.POST.get('id')
            name = request.POST.get('name')
            email = request.POST.get('email')
            username = request.POST.get('username')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            # Validate password confirmation
            if password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match'}, status=400)

            # Check for existing email or username
            if MobilePunchin.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already exists'}, status=400)
            if MobilePunchin.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)
            if MobilePunchin.objects.filter(id=id).exists():
                return JsonResponse({'error': 'ID already exists'}, status=400)

            # Create MobilePunchin record
            mobile_punchin = MobilePunchin(
                id=id,
                name=name,
                email=email,
                username=username,
            )
            mobile_punchin.set_password(password)
            mobile_punchin.save()

            return JsonResponse({'message': 'Mobile Punch-in ID created successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def list_mobile_punchin_ids(request):
    mobile_punchins = MobilePunchin.objects.all()
    logger.info(f"Queryset for mobile_punchins: {list(mobile_punchins.values())}")
    logger.info(f"Request type: {'AJAX' if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else 'Regular'}")
    return render(request, 'mobile_punchin/mobile_punchin_list.html', {'mobile_punchins': mobile_punchins})

def login_page(request):
    return render(request, 'mobile_punchin/login.html')

@csrf_exempt
def login_mobile_punchin(request):
    if request.method == 'POST':
        try:
            identifier = request.POST.get('identifier')
            password = request.POST.get('password')

            if not identifier or not password:
                logger.warning("Login attempt with missing credentials")
                return JsonResponse({'error': 'Both identifier and password are required'}, status=400)

            # Try to find user by username or email
            try:
                user = MobilePunchin.objects.get(username=identifier)
            except MobilePunchin.DoesNotExist:
                try:
                    user = MobilePunchin.objects.get(email=identifier)
                except MobilePunchin.DoesNotExist:
                    logger.warning(f"Login failed: No user found with identifier {identifier}")
                    return JsonResponse({'error': 'Invalid username or email'}, status=401)

            # Verify password
            if user.check_password(password):
                # Store user ID in session
                request.session['user_id'] = user.id
                request.session.modified = True
                logger.info(f"User {user.username} logged in successfully")
                return JsonResponse({'message': 'Login successful'}, status=200)
            else:
                logger.warning(f"Login failed: Incorrect password for identifier {identifier}")
                return JsonResponse({'error': 'Invalid password'}, status=401)

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def mainpage(request):
    return render(request,'mobile_punchin/main.html')