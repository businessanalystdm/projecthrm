from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import MobilePunchin, PunchRecord
from hr.models import Branches
import logging

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

            if password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match'}, status=400)
            if MobilePunchin.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already exists'}, status=400)
            if MobilePunchin.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)
            if MobilePunchin.objects.filter(id=id).exists():
                return JsonResponse({'error': 'ID already exists'}, status=400)

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
            logger.error(f"Create MobilePunchin error: {str(e)}")
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

            try:
                user = MobilePunchin.objects.get(username=identifier)
            except MobilePunchin.DoesNotExist:
                try:
                    user = MobilePunchin.objects.get(email=identifier)
                except MobilePunchin.DoesNotExist:
                    logger.warning(f"Login failed: No user found with identifier {identifier}")
                    return JsonResponse({'error': 'Invalid username or email'}, status=401)

            if user.check_password(password):
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
    user_id = request.session.get('user_id')
    if not user_id:
        logger.warning("Unauthorized access to mainpage")
        return redirect('time_tracker:login_page')

    try:
        user = MobilePunchin.objects.get(id=user_id)
    except MobilePunchin.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return redirect('time_tracker:login_page')

    today = timezone.localtime(timezone.now()).date()
    punch_record, created = PunchRecord.objects.get_or_create(user=user, date=today)

    is_punched_in = punch_record.punch_in_time is not None and punch_record.punch_out_time is None
    is_punched_out = punch_record.punch_out_time is not None
    branches = Branches.objects.all()
    context = {
        'user': user,
        'is_punched_in': is_punched_in,
        'is_punched_out': is_punched_out,
        'punch_record': punch_record,
        'current_date': today.isoformat(),
        'branches': branches,
    }
    return render(request, 'mobile_punchin/main.html', context)

@csrf_exempt
def punch_in(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                logger.error("Punch-in attempted without user_id in session")
                return JsonResponse({'error': 'User not authenticated'}, status=401)

            try:
                user = MobilePunchin.objects.get(id=user_id)
            except MobilePunchin.DoesNotExist:
                logger.error(f"User with ID {user_id} not found")
                return JsonResponse({'error': 'User not found'}, status=404)

            branch_id = request.POST.get('branch_id')
            if not branch_id:
                logger.warning(f"Punch-in attempted without branch_id for user {user.username}")
                return JsonResponse({'error': 'Branch selection required'}, status=400)

            try:
                branch = Branches.objects.get(id=branch_id)
            except Branches.DoesNotExist:
                logger.error(f"Branch with ID {branch_id} not found")
                return JsonResponse({'error': 'Invalid branch selected'}, status=400)

            today = timezone.localtime(timezone.now()).date()
            punch_record, created = PunchRecord.objects.get_or_create(user=user, date=today)

            if punch_record.punch_in_time:
                logger.warning(f"User {user.username} already punched in today")
                return JsonResponse({'error': 'Already punched in today'}, status=400)

            punch_record.punch_in_time = timezone.localtime(timezone.now())
            punch_record.punch_in_branch = branch
            punch_record.save()
            logger.info(f"User {user.username} punched in at {punch_record.punch_in_time} at branch {branch.name} on {punch_record.date}")
            return JsonResponse({
                'punch_in_time': punch_record.punch_in_time.isoformat(),
                'current_date': today.isoformat(),
                'punch_in_branch_name': branch.name
            })
        except Exception as e:
            logger.error(f"Punch-in error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def punch_out(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                logger.error("Punch-out attempted without user_id in session")
                return JsonResponse({'error': 'User not authenticated'}, status=401)

            try:
                user = MobilePunchin.objects.get(id=user_id)
            except MobilePunchin.DoesNotExist:
                logger.error(f"User with ID {user_id} not found")
                return JsonResponse({'error': 'User not found'}, status=404)

            branch_id = request.POST.get('branch_id')
            if not branch_id:
                logger.warning(f"Punch-out attempted without branch_id for user {user.username}")
                return JsonResponse({'error': 'Branch selection required'}, status=400)

            try:
                branch = Branches.objects.get(id=branch_id)
            except Branches.DoesNotExist:
                logger.error(f"Branch with ID {branch_id} not found")
                return JsonResponse({'error': 'Invalid branch selected'}, status=400)

            today = timezone.localtime(timezone.now()).date()
            try:
                punch_record = PunchRecord.objects.get(user=user, date=today)
                if not punch_record.punch_in_time or punch_record.punch_out_time:
                    logger.warning(f"User {user.username} has no active punch-in on {today}")
                    return JsonResponse({'error': 'No active punch-in record'}, status=400)

                punch_record.punch_out_time = timezone.localtime(timezone.now())
                punch_record.punch_out_branch = branch
                punch_record.save()
                logger.info(f"User {user.username} punched out at {punch_record.punch_out_time} at branch {branch.name} on {punch_record.date}")
                return JsonResponse({
                    'punch_out_time': punch_record.punch_out_time.isoformat(),
                    'current_date': today.isoformat(),
                    'punch_out_branch_name': branch.name
                })
            except PunchRecord.DoesNotExist:
                logger.warning(f"No punch record found for user {user.username} on {today}")
                return JsonResponse({'error': 'No punch-in record found'}, status=400)
        except Exception as e:
            logger.error(f"Punch-out error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        logger.info(f"User {user_id} logged out")
        request.session.flush()
        return JsonResponse({'message': 'Logged out successfully'}, status=200)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def list_punch_records(request):
    punch_records = PunchRecord.objects.select_related('user').all().order_by('-date', '-punch_in_time')
    return render(request, 'mobile_punchin/punch_records_list.html', {'punch_records': punch_records})