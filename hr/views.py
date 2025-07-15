from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import re
from datetime import date, timedelta
from django.db.models import Q
import decimal
from hr.models import CompanyName, Department, SubDepartment, Category, Qualification, Designation, \
    ZoneofOperations, Branches, Employee, Skill, Assets, BranchHistory, SalaryIncrementHistory, PromotionHistory
from django.views.decorators.csrf import csrf_exempt
from datetime import date
from django.utils import timezone
import json
from django.core.files.storage import FileSystemStorage
from django.core.validators import validate_email
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, HttpResponse
import logging
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models.functions import ExtractDay, ExtractMonth
from django.db.models import F, Case, When, Value, IntegerField, ExpressionWrapper, Count
from datetime import datetime
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from mobile_punchin.models import MobilePunchin

logger = logging.getLogger(__name__)


def is_superuser(user):
    return user.is_superuser


def json_response(data, status=200):
    return JsonResponse(data, status=status)


# Authentication Views
@method_decorator(never_cache, name='dispatch')
class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"
    redirect_field_name = "redirect_to"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()
        today_day = today.day
        today_month = today.month

        context['last_15_employees'] = Employee.objects.filter(emp_status="active").order_by('-emp_joining_date')[:15]
        context['last_15_resigned'] = Employee.objects.filter(emp_status='inactive',
                                                              emp_resigning_date__isnull=False).order_by(
            '-emp_resigning_date')[:15]
        context['birthday_employees'] = Employee.objects.filter(emp_status="active").annotate(
            day=ExtractDay('emp_dob'),
            month=ExtractMonth('emp_dob'),
            is_today=Case(
                When(day=today_day, month=today_month, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            days_until_birthday=ExpressionWrapper(
                Case(
                    When(month__gte=today_month, day__gte=today_day, then=(
                            (F('month') - today_month) * 30 + (F('day') - today_day)
                    )),
                    default=(
                            (F('month') - today_month + 12) * 30 + (F('day') - today_day)
                    ),
                    output_field=IntegerField()
                ),
                output_field=IntegerField()
            )
        ).order_by('is_today', 'days_until_birthday')[:15]
        context['now'] = timezone.now()
        context["companies"] = CompanyName.objects.filter(status='active')
        context["departments"] = Department.objects.filter(status='active').select_related('company_name')
        context["subdepartments"] = SubDepartment.objects.select_related('department', 'department__company_name').all()
        context["categories"] = Category.objects.select_related('sub_department', 'sub_department__department').all()
        context["zones"] = ZoneofOperations.objects.all()
        context["qualifications"] = Qualification.objects.all()
        context["designations"] = Designation.objects.select_related('category', 'category__sub_department').all()
        context["employees"] = Employee.objects.all()
        context["branches"] = Branches.objects.all()
        context["assets"] = Assets.objects.all()
        context["mobile_punchins"] = MobilePunchin.objects.all()

        messages = []
        employees = Employee.objects.select_related('emp_branch').filter(emp_status="active")
        for emp in employees:
            if emp.emp_dob.month == today_month and emp.emp_dob.day == today_day:
                messages.append({
                    'type': 'birthday',
                    'content': f"Today is {emp.emp_first_name} {emp.emp_last_name} in {emp.emp_branch.name}, wish them a delightful birthday!",
                    'time': 'Today'
                })
            if emp.emp_joining_date.month == today_month and emp.emp_joining_date.day == today_day:
                messages.append({
                    'type': 'anniversary',
                    'content': f"Today is {emp.emp_first_name} {emp.emp_last_name}'s work anniversary in {emp.emp_branch.name}, celebrate their milestone!",
                    'time': 'Today'
                })
        context['messages'] = messages

        print("Active employees:",
              [(emp.emp_first_name, emp.emp_last_name, emp.emp_joining_date) for emp in context['last_15_employees']])
        print("Resigned employees:",
              [(emp.emp_first_name, emp.emp_last_name, emp.emp_resigning_date) for emp in context['last_15_resigned']])
        print("Birthday employees:", [(emp.emp_first_name, emp.emp_last_name, emp.emp_dob,
                                       f"Day: {emp.day}, Month: {emp.month}, Is Today: {emp.is_today}, Days Until: {emp.days_until_birthday}")
                                      for emp in context['birthday_employees']])
        print("Messages:", messages)

        return context


# Company Management Views
@login_required(login_url='signin')
def company_name_list(request):
    companies = CompanyName.objects.all()
    return render(request, "partials/company_list.html", {'companies': companies})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_company_name(request):
    if request.method == "POST":
        name = request.POST.get('company_name')
        status = request.POST.get('status')
        if name and status:
            company = CompanyName.objects.create(company_name=name, status=status)
            return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_company_name(request, id):
    if request.method == 'POST':
        company = get_object_or_404(CompanyName, id=id)
        company.company_name = request.POST.get('company_name')
        company.status = request.POST.get('status')
        company.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_company_name(request, id):
    try:
        CompanyName.objects.get(id=id).delete()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False})


@login_required(login_url='signin')
def get_companies(request):
    try:
        companies = CompanyName.objects.all().values('id', 'company_name')
        return JsonResponse({'success': True, 'companies': list(companies)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Department Management Views
@login_required(login_url='signin')
def department_list(request):
    departments = Department.objects.all()
    return render(request, 'partials/department_list.html', {'departments': departments})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_department(request):
    if request.method == "POST":
        name = request.POST.get('department_name')
        company_id = request.POST.get('company_name')
        status = request.POST.get('status')
        if not name:
            return JsonResponse({'success': False, 'error': 'Department name is required'}, status=400)
        if not company_id:
            return JsonResponse({'success': False, 'error': 'Company is required'}, status=400)
        if not status:
            return JsonResponse({'success': False, 'error': 'Status is required'}, status=400)
        if status not in ['active', 'inactive']:
            return JsonResponse({'success': False, 'error': 'Invalid status value'}, status=400)
        try:
            company = get_object_or_404(CompanyName, id=company_id)
            department = Department.objects.create(
                department_name=name,
                company_name=company,
                status=status
            )
            return JsonResponse({
                'success': True,
                'department': {
                    'id': department.id,
                    'name': department.department_name,
                    'company_id': department.company_name.id,
                    'status': department.status
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_department(request, id):
    if request.method == "POST":
        dept = get_object_or_404(Department, id=id)
        name = request.POST.get('department_name')
        company_id = request.POST.get('company_name')
        status = request.POST.get('status')
        if name and company_id and status:
            company = get_object_or_404(CompanyName, id=company_id)
            dept.department_name = name
            dept.company_name = company
            dept.status = status
            dept.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_department(request, id):
    if request.method == "POST":
        get_object_or_404(Department, id=id).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
def get_departments_by_company(request, company_id):
    try:
        departments = Department.objects.filter(company_name_id=company_id, status='active').values('id',
                                                                                                    'department_name')
        return JsonResponse({'success': True, 'departments': list(departments)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'departments': []}, status=500)


# SubDepartment Management Views
@login_required(login_url='signin')
def subdepartment_list(request):
    subdepartments = SubDepartment.objects.select_related('department', 'department__company_name').all()
    return render(request, 'partials/sub_department_list.html', {'subdepartments': subdepartments})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_subdepartment(request):
    if request.method == "POST":
        name = request.POST.get('sub_department_name')
        department_id = request.POST.get('department')
        status = request.POST.get('status')
        if not (name and department_id and status):
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        try:
            department = get_object_or_404(Department, id=department_id)
            subdepartment = SubDepartment.objects.create(
                sub_department_name=name,
                department=department,
                status=status
            )
            return JsonResponse({
                'success': True,
                'subdepartment': {
                    'id': subdepartment.id,
                    'name': subdepartment.sub_department_name,
                    'department_id': subdepartment.department.id,
                    'status': subdepartment.status
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_subdepartment(request, id):
    if request.method == "POST":
        sub = get_object_or_404(SubDepartment, id=id)
        name = request.POST.get('sub_department_name')
        department_id = request.POST.get('department')
        status = request.POST.get('status')
        if not (name and department_id and status):
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        try:
            department = get_object_or_404(Department, id=department_id)
            sub.sub_department_name = name
            sub.department = department
            sub.status = status
            sub.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_subdepartment(request, id):
    if request.method == "POST":
        get_object_or_404(SubDepartment, id=id).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
def get_subdepartments_by_department(request, department_id):
    try:
        subdepartments = SubDepartment.objects.filter(department_id=department_id, status='active').values('id',
                                                                                                           'sub_department_name')
        return JsonResponse({'success': True, 'subdepartments': list(subdepartments)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'subdepartments': []}, status=500)


# Category Management Views
@login_required(login_url='signin')
def get_categories_by_subdepartment(request, subdepartment_id):
    try:
        categories = Category.objects.filter(sub_department_id=subdepartment_id, status='active').values('id',
                                                                                                         'category_name')
        return JsonResponse({'success': True, 'categories': list(categories)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'categories': []}, status=500)


@login_required(login_url='signin')
def category_list(request):
    categories = Category.objects.select_related('sub_department', 'sub_department__department').all()
    return render(request, "partials/category_list.html", {'categories': categories})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("category_name")
        sub_department_id = request.POST.get("sub_department")
        status = request.POST.get("status")
        if not (name and sub_department_id and status):
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        try:
            sub_department = get_object_or_404(SubDepartment, id=sub_department_id)
            category = Category.objects.create(
                category_name=name,
                sub_department=sub_department,
                status=status
            )
            return JsonResponse({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.category_name,
                    'sub_department_id': category.sub_department.id,
                    'status': category.status
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_category(request, id):
    if request.method == "POST":
        category = get_object_or_404(Category, id=id)
        name = request.POST.get("category_name")
        sub_department_id = request.POST.get("sub_department")
        status = request.POST.get("status")
        if not (name and sub_department_id and status):
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        try:
            sub_department = get_object_or_404(SubDepartment, id=sub_department_id)
            category.category_name = name
            category.sub_department = sub_department
            category.status = status
            category.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_category(request, id):
    if request.method == "POST":
        Category.objects.get(id=id).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required(login_url='signin')
def get_designations_by_category(request, category_id):
    try:
        designations = Designation.objects.filter(category_id=category_id, status='active').values('id', 'designation_name')
        return JsonResponse({'success': True, 'designations': list(designations)})
    except Exception as e:
        logger.error(f"Error fetching designations for category {category_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e), 'designations': []}, status=500)

@login_required(login_url='signin')
def designation_list(request):
    designations = Designation.objects.select_related(
        'category',
        'category__sub_department',
        'category__sub_department__department',
        'category__sub_department__department__company_name'
    ).all()
    return render(request, 'partials/designation_list.html', {'designations': designations})

@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
@require_POST
def add_designation(request):
    try:
        # Log POST data for debugging
        logger.debug(f"POST data: {dict(request.POST)}")

        designation_name = request.POST.get("designation_name", "").strip()
        category_id = request.POST.get("category")
        status = request.POST.get("status")
        rank = request.POST.get("rank", "1")

        if not (designation_name and category_id and status):
            logger.warning(
                f"Missing required fields: designation_name={designation_name}, category_id={category_id}, status={status}"
            )
            return JsonResponse({'success': False, 'error': 'Missing required fields: designation name, category, and status are required.'}, status=400)

        # Validate rank
        try:
            rank = int(rank)
            if rank < 1:
                return JsonResponse({'success': False, 'error': 'Rank must be at least 1.'}, status=400)
        except ValueError:
            logger.warning(f"Invalid rank value: {rank}")
            return JsonResponse({'success': False, 'error': 'Invalid rank value.'}, status=400)

        # Validate status
        if status not in ['active', 'inactive']:
            logger.warning(f"Invalid status: {status}")
            return JsonResponse({'success': False, 'error': 'Invalid status. Must be active or inactive.'}, status=400)

        # Validate category
        category = get_object_or_404(Category, id=category_id)

        with transaction.atomic():
            designation = Designation(
                designation_name=designation_name,
                category=category,
                status=status,
                rank=rank
            )
            designation.save()
            logger.info(f"Designation created: {designation_name} (ID: {designation.id})")

            return JsonResponse({
                'success': True,
                'designation': {
                    'id': designation.id,
                    'name': designation.designation_name,
                    'category_id': designation.category.id,
                    'status': designation.status,
                    'rank': designation.rank
                }
            })
    except Exception as e:
        logger.error(f"Unexpected error adding designation: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_designation(request, id):
    if request.method == "POST":
        designation = get_object_or_404(Designation, id=id)
        designation_name = request.POST.get("designation_name", "").strip()
        category_id = request.POST.get("category")
        status = request.POST.get("status")
        rank = request.POST.get("rank", "1")

        if not (designation_name and category_id and status):
            logger.warning(
                f"Missing required fields for update: designation_name={designation_name}, category_id={category_id}, status={status}"
            )
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

        try:
            category = get_object_or_404(Category, id=category_id)
            with transaction.atomic():
                designation.designation_name = designation_name
                designation.category = category
                designation.status = status
                designation.rank = int(rank) if rank else 1
                designation.save()  # Database-level unique_together will catch exact duplicates
                logger.info(f"Designation updated: {designation_name} (ID: {id})")

                return JsonResponse({'success': True})
        except IntegrityError as e:
            logger.error(f"Integrity error updating designation ID {id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f"Designation '{designation_name}' already exists in this category"
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating designation ID {id}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    logger.warning("Invalid method used for update_designation")
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)

@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_designation(request, id):
    if request.method == "POST":
        try:
            designation = get_object_or_404(Designation, id=id)
            designation.delete()
            logger.info(f"Designation deleted: ID {id}")
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error deleting designation ID {id}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    logger.warning("Invalid method used for delete_designation")
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)

@login_required(login_url='signin')
def designation_modal(request):
    companies = CompanyName.objects.all()
    departments = Department.objects.all()
    subdepartments = SubDepartment.objects.select_related('department').all()
    categories = Category.objects.select_related('sub_department').all()
    return render(request, 'partials/designation_modal.html', {
        'companies': companies,
        'departments': departments,
        'subdepartments': subdepartments,
        'categories': categories,
    })

# Qualification Management Views
@login_required(login_url='signin')
def qualification_list(request):
    qualifications = Qualification.objects.all()
    return render(request, 'partials/qualification_list.html', {'qualifications': qualifications})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_qualification(request):
    if request.method == "POST":
        name = request.POST.get('qualification_name')
        status = request.POST.get('status')
        if name and status:
            Qualification.objects.create(qualification_name=name, status=status)
            return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_qualification(request, id):
    if request.method == "POST":
        qualification = get_object_or_404(Qualification, id=id)
        qualification.qualification_name = request.POST.get('qualification_name')
        qualification.status = request.POST.get('status')
        qualification.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_qualification(request, id):
    if request.method == "POST":
        qualification = get_object_or_404(Qualification, id=id)
        qualification.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


# Zone Management Views
@login_required(login_url='signin')
def zone_list(request):
    zones = ZoneofOperations.objects.all()
    return render(request, 'partials/zone_list.html', {'zones': zones})


@csrf_exempt
@login_required(login_url='signin')
# @user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_zone(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        status = request.POST.get('status')
        ZoneofOperations.objects.create(name=name, status=status)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_zone(request, id):
    if request.method == 'POST':
        zone = get_object_or_404(ZoneofOperations, id=id)
        zone.name = request.POST.get('name')
        zone.status = request.POST.get('status')
        zone.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_zone(request, id):
    if request.method == 'POST':
        zone = get_object_or_404(ZoneofOperations, id=id)
        zone.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


# Branch Management Views
@login_required(login_url='signin')
def branches_list(request):
    branches = Branches.objects.select_related('zone').all()
    return render(request, 'partials/branches_list.html', {'branches': branches})


@login_required(login_url='signin')
# @user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_branch(request):
    if request.method == "POST":
        name = request.POST.get('name')
        code = request.POST.get('code')
        zone_id = request.POST.get('zone')
        status = request.POST.get('status')
        Branches.objects.create(
            name=name,
            code=code,
            zone_id=zone_id,
            status=status
        )
        return JsonResponse({'success': True})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def update_branch(request, id):
    if request.method == "POST":
        branch = get_object_or_404(Branches, id=id)
        branch.name = request.POST.get('name')
        branch.code = request.POST.get('code')
        branch.zone_id = request.POST.get('zone')
        branch.status = request.POST.get('status')
        branch.save()
        return JsonResponse({'success': True})


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_branch(request, id):
    if request.method == "POST":
        branch = get_object_or_404(Branches, id=id)
        branch.delete()
        return JsonResponse({'success': True})


# Employee Management Views
@login_required(login_url='signin')
def employee_form(request, employee_id=None):
    if employee_id:
        employee = get_object_or_404(Employee, id=employee_id)
    else:
        employee = None
    context = {
        'employee': employee,
        'qualifications': Qualification.objects.all(),
        'companies': CompanyName.objects.all(),
        'branches': Branches.objects.all(),
        'departments': Department.objects.all(),
        'subdepartments': SubDepartment.objects.select_related('department').all(),
        'categories': Category.objects.select_related('sub_department').all(),
        'designations': Designation.objects.select_related('category').all(),
        'assets': Assets.objects.filter(status='active'),
    }
    return render(request, 'partials/employee.html', context)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
@require_POST
def add_employee(request):
    try:
        # Extract POST data
        emp_id_branch = request.POST.get('emp_id_branch')
        emp_first_name = request.POST.get('emp_first_name')
        emp_last_name = request.POST.get('emp_last_name', '')
        emp_aadhar_number = request.POST.get('emp_aadhar_number', '')
        emp_dob = request.POST.get('emp_dob')
        emp_gender = request.POST.get('emp_gender')
        emp_mobile = request.POST.get('emp_mobile')
        emp_second_mobile = request.POST.get('emp_second_mobile', '')
        emp_email = request.POST.get('emp_email')
        emp_blood_group = request.POST.get('emp_blood_group')
        emp_qualification_id = request.POST.get('emp_qualification')
        emp_address = request.POST.get('emp_address')
        emp_company_id = request.POST.get('emp_company')
        emp_branch_id = request.POST.get('emp_branch')
        emp_department_id = request.POST.get('emp_department')
        emp_sub_department_id = request.POST.get('emp_sub_department')
        emp_category_id = request.POST.get('emp_category')
        emp_designation_id = request.POST.get('emp_designation')
        emp_salary = request.POST.get('emp_salary')
        emp_joining_date = request.POST.get('emp_joining_date')
        emp_resigning_date = request.POST.get('emp_resigning_date', None)
        emp_resigning_reason = request.POST.get('emp_resigning_reason', '')
        emp_work_start_time = request.POST.get('emp_work_start_time', None)
        emp_work_end_time = request.POST.get('emp_work_end_time', None)
        emp_extra_skills_json = request.POST.get('emp_extra_skills', '[]')
        emp_experiences = request.POST.get('emp_experiences', '[]')
        emp_status = request.POST.get('emp_status')
        emp_remarks = request.POST.get('emp_remarks')
        employee_id = request.POST.get('employee_id')
        assigned_assets = request.POST.get('assigned_assets', '[]')

        # Validation
        required_fields = [
            emp_id_branch, emp_first_name, emp_dob, emp_mobile,
            emp_gender, emp_qualification_id, emp_address, emp_company_id,
            emp_branch_id, emp_department_id, emp_sub_department_id, emp_category_id,
            emp_designation_id, emp_joining_date, emp_work_start_time, emp_work_end_time, emp_salary
        ]
        if not all(required_fields):
            return JsonResponse({'success': False, 'error': 'Missing required fields.'})

        # Validate email
        try:
            validate_email(emp_email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email address.'})

        # Validate phone numbers
        phone_regex = r'^\+?\d{10,15}$'
        if not re.match(phone_regex, emp_mobile):
            return JsonResponse({'success': False, 'error': 'Invalid mobile number.'})
        if emp_second_mobile and not re.match(phone_regex, emp_second_mobile):
            return JsonResponse({'success': False, 'error': 'Invalid secondary mobile number.'})

        # Validate employee ID
        id_regex = r'^\d{7}$'
        if not re.match(id_regex, emp_id_branch):
            return JsonResponse({'success': False, 'error': 'Employee ID must be exactly 7 digits.'})

        # Validate and convert date fields
        def parse_date(date_str):
            if date_str and date_str.strip():
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValidationError(f"Invalid date format for {date_str}. Use YYYY-MM-DD.")
            return None

        try:
            dob = parse_date(emp_dob)
            joining_date = parse_date(emp_joining_date)
            resigning_date = parse_date(emp_resigning_date)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        if not dob or not joining_date:
            return JsonResponse({'success': False, 'error': 'Date of birth and joining date are required.'})

        # Parse JSON fields
        try:
            experiences = json.loads(emp_experiences) if emp_experiences else []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for emp_experiences: {emp_experiences}, Error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid experiences format.'})

        try:
            assigned_asset_ids = json.loads(assigned_assets) if assigned_assets else []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for assigned_assets: {assigned_assets}, Error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid assigned assets format.'})

        try:
            skill_names = json.loads(emp_extra_skills_json) if emp_extra_skills_json else []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for emp_extra_skills: {emp_extra_skills_json}, Error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid skills format.'})

        # Process skills
        skill_objects = []
        for name in skill_names:
            if name.strip():
                skill, created = Skill.objects.get_or_create(name=name.strip(), defaults={'description': None})
                skill_objects.append(skill)

        # Fetch related objects
        qualification = get_object_or_404(Qualification, id=emp_qualification_id)
        company = get_object_or_404(CompanyName, id=emp_company_id)
        branch = get_object_or_404(Branches, id=emp_branch_id)
        department = get_object_or_404(Department, id=emp_department_id)
        sub_department = get_object_or_404(SubDepartment, id=emp_sub_department_id)
        category = get_object_or_404(Category, id=emp_category_id)
        designation = get_object_or_404(Designation, id=emp_designation_id)

        # Validate hierarchy
        if department.company_name != company:
            return JsonResponse({'success': False, 'error': 'Department does not belong to selected company.'})
        if sub_department.department != department:
            return JsonResponse({'success': False, 'error': 'Sub-department does not belong to selected department.'})
        if category.sub_department != sub_department:
            return JsonResponse({'success': False, 'error': 'Category does not belong to selected sub-department.'})
        if designation.category != category:
            return JsonResponse({'success': False, 'error': 'Designation does not belong to selected category.'})

        with transaction.atomic():
            if employee_id:
                # Update existing employee
                employee = get_object_or_404(Employee, id=employee_id)
                promotion_changed = (
                    employee.emp_department_id != int(emp_department_id) or
                    employee.emp_sub_department_id != int(emp_sub_department_id) or
                    employee.emp_category_id != int(emp_category_id) or
                    employee.emp_designation_id != int(emp_designation_id)
                )
                salary_changed = employee.emp_salary != decimal.Decimal(emp_salary)
                branch_changed = employee.emp_branch_id != int(emp_branch_id)

                # Update employee fields
                employee.emp_id_branch = emp_id_branch
                employee.emp_first_name = emp_first_name
                employee.emp_last_name = emp_last_name
                employee.emp_aadhar_number = emp_aadhar_number if emp_aadhar_number else None
                employee.emp_dob = dob
                employee.emp_gender = emp_gender
                employee.emp_mobile = emp_mobile
                employee.emp_second_mobile = emp_second_mobile if emp_second_mobile else None
                employee.emp_email = emp_email
                employee.emp_blood_group = emp_blood_group
                employee.emp_qualification = qualification
                employee.emp_address = emp_address
                employee.emp_company = company
                employee.emp_branch = branch
                employee.emp_department = department
                employee.emp_sub_department = sub_department
                employee.emp_category = category
                employee.emp_designation = designation
                employee.emp_salary = decimal.Decimal(emp_salary)
                employee.emp_joining_date = joining_date
                employee.emp_resigning_date = resigning_date
                employee.emp_resigning_reason = emp_resigning_reason if emp_resigning_reason else None
                employee.emp_work_start_time = emp_work_start_time
                employee.emp_work_end_time = emp_work_end_time
                employee.emp_experiences = experiences
                employee.emp_status = emp_status
                employee.emp_remarks = emp_remarks

                # Handle photo upload
                if 'emp_photo' in request.FILES:
                    photo = request.FILES['emp_photo']
                    fs = FileSystemStorage()
                    filename = fs.save(photo.name, photo)
                    employee.emp_photo = filename

                # Handle documents upload
                if 'emp_documents' in request.FILES:
                    document = request.FILES['emp_documents']
                    fs = FileSystemStorage()
                    filename = fs.save(document.name, document)
                    employee.emp_documents = filename

                # Save employee
                employee.save()

                # Handle PromotionHistory
                if promotion_changed:
                    current_promotion = PromotionHistory.objects.filter(
                        employee=employee,
                        end_date__isnull=True,
                        status='active'
                    ).first()
                    if current_promotion:
                        current_promotion.end_date = joining_date - timedelta(days=1)
                        current_promotion.status = 'inactive'
                        current_promotion.save()
                    PromotionHistory.objects.create(
                        employee=employee,
                        department=department,
                        sub_department=sub_department,
                        category=category,
                        designation=designation,
                        start_date=joining_date,
                        end_date=None,
                        status='active'
                    )

                # Handle SalaryIncrementHistory
                if salary_changed:
                    current_salary_history = SalaryIncrementHistory.objects.filter(
                        employee=employee,
                        end_date__isnull=True,
                        status='active'
                    ).first()
                    if current_salary_history:
                        current_salary_history.end_date = joining_date
                        current_salary_history.status = 'inactive'
                        current_salary_history.save()
                    SalaryIncrementHistory.objects.create(
                        employee=employee,
                        salary=decimal.Decimal(emp_salary),
                        start_date=joining_date,
                        end_date=None,
                        status='active'
                    )

                # Handle BranchHistory
                if branch_changed:
                    current_branch_history = BranchHistory.objects.filter(
                        employee=employee,
                        end_date__isnull=True,
                        status='active'
                    ).first()
                    if current_branch_history:
                        current_branch_history.end_date = joining_date
                        current_branch_history.status = 'inactive'
                        current_branch_history.save()
                    BranchHistory.objects.create(
                        employee=employee,
                        branch=branch,
                        start_date=joining_date,
                        end_date=None,
                        status='active'
                    )
            else:
                # Create new employee
                employee = Employee(
                    emp_id_branch=emp_id_branch,
                    emp_first_name=emp_first_name,
                    emp_last_name=emp_last_name,
                    emp_aadhar_number=emp_aadhar_number if emp_aadhar_number else None,
                    emp_dob=dob,
                    emp_gender=emp_gender,
                    emp_mobile=emp_mobile,
                    emp_second_mobile=emp_second_mobile if emp_second_mobile else None,
                    emp_email=emp_email,
                    emp_blood_group=emp_blood_group,
                    emp_qualification=qualification,
                    emp_address=emp_address,
                    emp_company=company,
                    emp_branch=branch,
                    emp_department=department,
                    emp_sub_department=sub_department,
                    emp_category=category,
                    emp_designation=designation,
                    emp_salary=decimal.Decimal(emp_salary),
                    emp_joining_date=joining_date,
                    emp_resigning_date=resigning_date,
                    emp_resigning_reason=emp_resigning_reason if emp_resigning_reason else None,
                    emp_work_start_time=emp_work_start_time,
                    emp_work_end_time=emp_work_end_time,
                    emp_experiences=experiences,
                    emp_status=emp_status,
                    emp_remarks=emp_remarks
                )

                if 'emp_photo' in request.FILES:
                    photo = request.FILES['emp_photo']
                    fs = FileSystemStorage()
                    filename = fs.save(photo.name, photo)
                    employee.emp_photo = filename

                if 'emp_documents' in request.FILES:
                    document = request.FILES['emp_documents']
                    fs = FileSystemStorage()
                    filename = fs.save(document.name, document)
                    employee.emp_documents = filename

                employee.save()

            # Assign skills and assets
            employee.emp_extra_skills.set(skill_objects)
            if assigned_asset_ids:
                assets = Assets.objects.filter(id__in=assigned_asset_ids, status='active')
                employee.emp_assets.set(assets)

        return JsonResponse({'success': True, 'message': 'Employee saved successfully.'})
    except Exception as e:
        logger.error(f"Error in add_employee: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='signin')
def list_employees(request):
    # Optimize employee query with select_related to fetch related models
    employees = Employee.objects.filter(emp_status='active').select_related(
        'emp_company',
        'emp_branch',
        'emp_branch__zone',
        'emp_department',
        'emp_sub_department',
        'emp_category',
        'emp_designation',  # Critical for data-designation-rank
        'emp_qualification'
    ).prefetch_related('emp_extra_skills').order_by('-emp_joining_date')

    # Fetch filter dropdown data with minimal queries
    branches = Branches.objects.filter(status='active').select_related('zone')
    companies = CompanyName.objects.filter(status='active')
    departments = Department.objects.filter(status='active').select_related('company_name')
    sub_departments = SubDepartment.objects.filter(status='active').select_related('department')
    categories = Category.objects.filter(status='active').select_related('sub_department')
    qualifications = Qualification.objects.filter(status='active')
    zones = ZoneofOperations.objects.filter(status='active')
    designations = Designation.objects.filter(status='active').select_related('category')

    # Message for no branches
    no_branches_message = "No active branches available. Please add a branch first." if not branches.exists() else None

    context = {
        'employees': employees,
        'branches': branches,
        'companies': companies,
        'departments': departments,
        'sub_departments': sub_departments,
        'categories': categories,
        'qualifications': qualifications,
        'zones': zones,
        'designations': designations,
        'no_branches_message': no_branches_message,
    }
    return render(request, 'partials/employee_list.html', context)


@login_required(login_url='signin')
@require_GET
def get_employee_details(request):
    employee_id = request.GET.get('id')
    try:
        employee = Employee.objects.get(id=employee_id)
        return render(request, 'partials/employee_view.html', {'employee': employee})
    except Employee.DoesNotExist:
        logger.error(f"Employee not found for ID: {employee_id}")
        return HttpResponse('Employee not found', status=404)
    except Exception as e:
        logger.error(f"Error fetching employee: {str(e)}")
        return HttpResponse(f'Error: {str(e)}', status=500)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
@require_POST
def delete_employee(request, employee_id):
    try:
        with transaction.atomic():
            employee = get_object_or_404(Employee, id=employee_id)
            if employee.emp_assets.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot delete employee with assigned assets. Please remove assets first.'
                }, status=400)
            logger.info(
                f"Deleting employee ID: {employee_id}, Name: {employee.emp_first_name} {employee.emp_last_name}")
            employee.delete()
            return JsonResponse({
                'success': True,
                'message': 'Employee deleted successfully.'
            })
    except Exception as e:
        logger.error(f"Error deleting employee {employee_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
@require_POST
def resign_employee(request):
    try:
        employee_id = request.POST.get('employee_id')
        resigning_date_str = request.POST.get('emp_resigning_date')
        logger.debug(f"Received employee_id: {employee_id}, emp_resigning_date: {resigning_date_str}")

        if not employee_id:
            logger.warning("Missing employee_id in resign_employee request")
            return JsonResponse({'success': False, 'error': 'Employee ID is required.'}, status=400)

        if not resigning_date_str:
            logger.warning("Missing emp_resigning_date in resign_employee request")
            return JsonResponse({'success': False, 'error': 'Resignation date is required.'}, status=400)

        try:
            resigning_date = datetime.strptime(resigning_date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid emp_resigning_date format: {resigning_date_str}")
            return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        if resigning_date >= timezone.now().date():
            logger.warning(f"Future emp_resigning_date: {resigning_date}")
            return JsonResponse({'success': False, 'error': 'Resignation date cannot be in the future.'}, status=400)

        employee = get_object_or_404(Employee, id=employee_id)
        if employee.emp_status == 'inactive':
            logger.info(f"Employee {employee_id} is already resigned")
            return JsonResponse({'success': False, 'error': 'Employee is already resigned.'}, status=400)

        with transaction.atomic():
            employee.emp_status = 'inactive'
            employee.emp_resigning_date = resigning_date
            employee.emp_assets.clear()
            employee.save()

        logger.info(f"Employee {employee_id} marked as resigned with emp_resigning_date: {resigning_date}")
        return JsonResponse({'success': True, 'message': 'Employee marked as resigned successfully.'})
    except Exception as e:
        logger.error(f"Error in resign_employee: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Asset Management Views
@login_required(login_url='signin')
def assets_modal(request):
    context = {
        'assets': Assets.objects.filter(status='active'),
    }
    return render(request, 'partials/assets_modal.html', context)


def asset_list(request):
    assets = Assets.objects.filter(status='active').values('id', 'name')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'assets': [{'id': asset['id'], 'name': asset['name'], 'status': 'active'} for asset in assets]
        })
    return render(request, 'partials/assets_list.html', {'assets': Assets.objects.all()})


@require_POST
@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def add_asset(request):
    try:
        asset_name = request.POST.get('asset_name')
        status = request.POST.get('status', 'active')
        if not asset_name:
            return JsonResponse({'success': False, 'error': 'Asset name is required.'})
        asset = Assets.objects.create(name=asset_name, status=status)
        return JsonResponse({
            'success': True,
            'message': 'Asset added successfully.',
            'asset_id': asset.id,
            'asset_name': asset.name
        })
    except Exception as e:
        logger.error(f"Error in add_asset: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def delete_asset(request):
    try:
        asset_id = request.POST.get('asset_id')
        if not asset_id:
            return JsonResponse({'success': False, 'error': 'Asset ID is required.'})
        asset = get_object_or_404(Assets, id=asset_id)
        asset.delete()
        return JsonResponse({'success': True, 'message': 'Asset deleted successfully.'})
    except Exception as e:
        logger.error(f"Error in delete_asset: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def assign_asset(request):
    try:
        employee_id = request.POST.get('employee_id')
        asset_id = request.POST.get('asset_id')
        if not asset_id:
            return JsonResponse({'success': False, 'error': 'Asset ID is required.'})
        if not employee_id:
            return JsonResponse({'success': True, 'message': 'Asset assignment tracked locally.'})
        employee = get_object_or_404(Employee, id=employee_id)
        asset = get_object_or_404(Assets, id=asset_id)
        if asset in employee.emp_assets.all():
            return JsonResponse({'success': False, 'error': 'Asset already assigned.'})
        employee.emp_assets.add(asset)
        return JsonResponse({'success': True, 'message': 'Asset assigned successfully.'})
    except Exception as e:
        logger.error(f"Error in assign_asset: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def remove_asset(request):
    try:
        employee_id = request.POST.get('employee_id')
        asset_id = request.POST.get('asset_id')
        if not (employee_id and asset_id):
            return JsonResponse({'success': False, 'error': 'Employee ID and Asset ID are required.'})
        employee = get_object_or_404(Employee, id=employee_id)
        asset = get_object_or_404(Assets, id=asset_id)
        if asset not in employee.emp_assets.all():
            return JsonResponse({'success': False, 'error': 'Asset not assigned to this employee.'})
        employee.emp_assets.remove(asset)
        return JsonResponse({'success': True, 'message': 'Asset removed successfully.'})
    except Exception as e:
        logger.error(f"Error in remove_asset: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='signin')
@require_GET
def get_employee_assets(request):
    try:
        employee_id = request.GET.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'error': 'Employee ID is required.'}, status=400)
        employee = get_object_or_404(Employee, id=employee_id)
        assets = employee.emp_assets.filter(status='active').values('id', 'name')
        return JsonResponse({'success': True, 'assets': list(assets)})
    except Exception as e:
        logger.error(f"Error in get_employee_assets: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Skill Management Views
def skill_list(request):
    query = request.GET.get('query', '')
    skills = Skill.objects.filter(name__icontains=query)[:10]
    return JsonResponse({'skills': [{'id': skill.id, 'name': skill.name} for skill in skills]})


# Miscellaneous Views
@login_required(login_url='signin')
def index(request):
    if request.method == 'POST':
        pass
    return render(request, 'index.html')


@login_required(login_url='signin')
def employee_list_api(request):
    employees = Employee.objects.select_related('emp_branch').filter(emp_status="active")
    data = [
        {
            'id': emp.id,
            'emp_first_name': emp.emp_first_name,
            'emp_last_name': emp.emp_last_name or '',
            'branch': {'name': emp.emp_branch.name} if emp.emp_branch else {'name': 'N/A'},
            'emp_dob': emp.emp_dob.strftime('%Y-%m-%d') if emp.emp_dob else None,
            'emp_joining_date': emp.emp_joining_date.strftime('%Y-%m-%d') if emp.emp_joining_date else None
        }
        for emp in employees
    ]
    return JsonResponse(data, safe=False)


@login_required(login_url='signin')
@require_GET
def employee_details(request, id):
    try:
        employee = Employee.objects.select_related('emp_branch', 'emp_department').get(id=id)
        data = {
            'success': True,
            'employee': {
                'id': employee.id,
                'emp_first_name': employee.emp_first_name,
                'emp_last_name': employee.emp_last_name or '',
                'emp_dob': employee.emp_dob.strftime('%b %d, %Y') if employee.emp_dob else None,
                'emp_joining_date': employee.emp_joining_date.strftime('%b %d, %Y'),
                'emp_resigning_date': employee.emp_resigning_date.strftime(
                    '%b %d, %Y') if employee.emp_resigning_date else None,
                'department': employee.emp_department.department_name if employee.emp_department else 'N/A',
                'email': employee.emp_email or 'N/A',
                'branch': employee.emp_branch.name if employee.emp_branch else 'N/A'
            }
        }
    except Employee.DoesNotExist:
        data = {'success': False, 'error': 'Employee not found'}
    return JsonResponse(data)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
@require_GET
def get_employee_for_edit(request, employee_id):
    try:
        employee = get_object_or_404(Employee, id=employee_id)
        data = {
            'success': True,
            'employee': {
                'id': employee.id,
                'emp_id_branch': employee.emp_id_branch,
                'emp_first_name': employee.emp_first_name,
                'emp_last_name': employee.emp_last_name or '',
                'emp_aadhar_number': employee.emp_aadhar_number or '',
                'emp_dob': employee.emp_dob.strftime('%Y-%m-%d') if employee.emp_dob else '',
                'emp_gender': employee.emp_gender,
                'emp_mobile': employee.emp_mobile,
                'emp_second_mobile': employee.emp_second_mobile or '',
                'emp_email': employee.emp_email,
                'emp_blood_group': employee.emp_blood_group,
                'emp_qualification': {'id': employee.emp_qualification.id},
                'emp_address': employee.emp_address,
                'emp_company': {'id': employee.emp_company.id},
                'emp_branch': {'id': employee.emp_branch.id},
                'emp_department': {'id': employee.emp_department.id},
                'emp_sub_department': {'id': employee.emp_sub_department.id},
                'emp_category': {'id': employee.emp_category.id},
                'emp_designation': {
                    'id': employee.emp_designation.id,
                    'designation_name': employee.emp_designation.designation_name if employee.emp_designation else None
                },
                'emp_salary': str(employee.emp_salary),
                'emp_joining_date': employee.emp_joining_date.strftime('%Y-%m-%d'),
                'emp_resigning_date': employee.emp_resigning_date.strftime(
                    '%Y-%m-%d') if employee.emp_resigning_date else '',
                'emp_work_start_time': employee.emp_work_start_time.strftime(
                    '%H:%M') if employee.emp_work_start_time else '',
                'emp_work_end_time': employee.emp_work_end_time.strftime('%H:%M') if employee.emp_work_end_time else '',
                'emp_extra_skills': [{'id': skill.id, 'name': skill.name} for skill in employee.emp_extra_skills.all()],
                'emp_experiences': employee.emp_experiences or [],
                'emp_status': employee.emp_status,
                'emp_photo': employee.emp_photo.url if employee.emp_photo else None,
                'emp_assets': [{'id': asset.id, 'name': asset.name} for asset in employee.emp_assets.all()],
            }
        }
        return JsonResponse(data)
    except Employee.DoesNotExist:
        logger.error(f"Employee not found for ID: {employee_id}")
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching employee for edit: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='signin')
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
@require_POST
def transfer_branch(request):
    logger.info(f"Received POST request: {request.POST}, server date: {date.today()}")
    employee_id = request.POST.get('employee_id')
    branch_id = request.POST.get('branch_id')
    start_date = request.POST.get('start_date')

    if not all([employee_id, branch_id, start_date]):
        logger.error(
            f"Missing required fields: employee_id={employee_id}, branch_id={branch_id}, start_date={start_date}")
        return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

    try:
        with transaction.atomic():
            employee = Employee.objects.get(id=employee_id)
            new_branch = Branches.objects.get(id=branch_id)
            logger.info(f"Found employee: {employee}, new_branch: {new_branch}")

            start_date = date.fromisoformat(start_date)
            logger.info(f"Parsed start_date: {start_date}, today: {date.today()}")

            if start_date < date.today():
                logger.error(f"Start date {start_date} is before today {date.today()}")
                return JsonResponse({'success': False, 'error': 'Start date must be today or in the future'},
                                    status=400)

            if employee.emp_branch == new_branch:
                logger.error(f"Employee already assigned to branch: {new_branch}")
                return JsonResponse({'success': False, 'error': 'Employee is already assigned to this branch'},
                                    status=400)

            current_history = BranchHistory.objects.filter(
                employee=employee,
                end_date__isnull=True,
                status='active'
            ).first()
            if current_history:
                current_history.end_date = start_date
                current_history.status = 'inactive'
                current_history.save()
                logger.info(f"Updated current branch history: {current_history}")

            BranchHistory.objects.create(
                employee=employee,
                branch=new_branch,
                start_date=start_date,
                status='active'
            )
            employee.emp_branch = new_branch
            employee.save()
            logger.info(f"Branch transfer completed for employee: {employee}")
            return JsonResponse({'success': True, 'message': 'Branch transfer completed'})

    except Employee.DoesNotExist:
        logger.error(f"Employee not found: id={employee_id}")
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
    except Branches.DoesNotExist:
        logger.error(f"Branch not found: id={branch_id}")
        return JsonResponse({'success': False, 'error': 'Branch not found'}, status=404)
    except ValueError as ve:
        logger.error(f"Invalid date format: {start_date}, error: {str(ve)}")
        return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='signin')
@require_GET
def get_employee_details_for_upgrade(request):
    employee_id = request.GET.get('employee_id')
    if not employee_id:
        logger.error("Missing employee_id parameter")
        return JsonResponse({'success': False, 'error': 'Employee ID is required'}, status=400)

    try:
        employee = Employee.objects.get(id=employee_id)
        response_data = {
            'success': True,
            'employee': {
                'branch_id': employee.emp_branch.id if employee.emp_branch else None,
                'branch_name': employee.emp_branch.name if employee.emp_branch else None,
                'emp_salary': float(employee.emp_salary) if employee.emp_salary else None,
                'department_id': employee.emp_department.id if employee.emp_department else None,
                'department_name': employee.emp_department.department_name if employee.emp_department else None,
                'sub_department_id': employee.emp_sub_department.id if employee.emp_sub_department else None,
                'sub_department_name': employee.emp_sub_department.sub_department_name if employee.emp_sub_department else None,
                'category_id': employee.emp_category.id if employee.emp_category else None,
                'category_name': employee.emp_category.category_name if employee.emp_category else None,
                'designation_id': employee.emp_designation.id if employee.emp_designation else None,
                'designation_name': employee.emp_designation.designation_name if employee.emp_designation else None,
                'emp_company': {
                    'id': employee.emp_company.id if employee.emp_company else None,
                    'company_name': employee.emp_company.company_name if employee.emp_company else None
                },
                'emp_joining_date': employee.emp_joining_date.strftime('%Y-%m-%d') if employee.emp_joining_date else None
            }
        }
        logger.info(f"Fetched employee details for upgrade: ID={employee_id}")
        return JsonResponse(response_data)
    except Employee.DoesNotExist:
        logger.error(f"Employee not found: ID={employee_id}")
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching employee details for upgrade: ID={employee_id}, Error={str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='signin')
@require_GET
def list_employees_with_history(request):
    try:
        employee_id = request.GET.get('employee_id')
        employees = Employee.objects.filter(
            emp_resigning_date__isnull=True
        )

        if employee_id:
            # Validate emp_id_branch format (7 digits)
            if not re.match(r'^\d{7}$', employee_id):
                logger.error(f"Invalid emp_id_branch format: {employee_id}")
                return render(request, 'partials/employee_history_list.html', {
                    'employees_with_transfers': [],
                    'error': 'Employee ID must be exactly 7 digits'
                })
            employees = employees.filter(emp_id_branch=employee_id)
            if not employees.exists():
                logger.info(f"No employee found with emp_id_branch: {employee_id}")
                return render(request, 'partials/employee_history_list.html', {
                    'employees_with_transfers': [],
                    'error': f'No employee found with Employee ID: {employee_id}'
                })

        employees = employees.filter(
            Q(branch_history__isnull=False) |
            Q(salary_increment_history__isnull=False) |
            Q(promotion_history__isnull=False)
        ).annotate(
            branch_history_count=Count('branch_history', distinct=True),
            salary_history_count=Count('salary_increment_history', distinct=True),
            promotion_history_count=Count('promotion_history', distinct=True)
        ).filter(
            Q(branch_history_count__gt=1) |
            Q(salary_history_count__gt=1) |
            Q(promotion_history_count__gt=1)
        ).select_related('emp_designation', 'emp_branch').distinct()

        employee_details = [
            f"ID: {emp.id}, emp_id_branch: {emp.emp_id_branch}, "
            f"Name: {emp.emp_first_name} {emp.emp_last_name or ''}, "
            f"Designation: {emp.emp_designation.designation_name if emp.emp_designation else 'None'}, "
            f"Branch: {emp.emp_branch.name if emp.emp_branch else 'None'}, "
            f"BranchHistory count: {emp.branch_history_count}, "
            f"SalaryIncrementHistory count: {emp.salary_history_count}, "
            f"PromotionHistory count: {emp.promotion_history_count}"
            for emp in employees
        ]
        logger.info(
            f"list_employees_with_history: Found {employees.count()} employees with multiple "
            f"branch transfers, salary increments, or promotions: {employee_details}"
        )

        all_employees = Employee.objects.filter(
            emp_resigning_date__isnull=True
        ).annotate(
            branch_count=Count('branch_history', distinct=True),
            salary_count=Count('salary_increment_history', distinct=True),
            promotion_count=Count('promotion_history', distinct=True)
        ).values('id', 'emp_id_branch', 'emp_first_name', 'emp_last_name', 'branch_count', 'salary_count', 'promotion_count')
        all_employee_details = [
            f"ID: {emp['id']}, emp_id_branch: {emp['emp_id_branch']}, "
            f"Name: {emp['emp_first_name']} {emp['emp_last_name'] or ''}, "
            f"BranchCount: {emp['branch_count']}, SalaryCount: {emp['salary_count']}, PromotionCount: {emp['promotion_count']}"
            for emp in all_employees
        ]
        logger.debug(
            f"All active employees with history counts: {all_employee_details}"
        )

        context = {
            'employees_with_transfers': employees,
            'error': None
        }
        return render(request, 'partials/employee_history_list.html', context)
    except Exception as e:
        logger.error(f"Error in list_employees_with_history: {str(e)}")
        return render(request, 'partials/employee_history_list.html', {
            'employees_with_transfers': [],
            'error': f'Error: {str(e)}'
        }, status=500)


@login_required(login_url='signin')
@require_GET
def get_employee_branch_history(request):
    try:
        employee_id = request.GET.get('employee_id')
        if not employee_id:
            logger.error("Missing employee_id parameter")
            return render(request, 'partials/branch_history.html', {
                'error': 'Employee ID is required',
                'branch_history': []
            }, status=400)

        employee = get_object_or_404(Employee, id=employee_id)
        branch_history = BranchHistory.objects.filter(employee=employee).select_related('branch').order_by('start_date')

        logger.info(f"Fetched {branch_history.count()} branch history records for employee ID: {employee_id}")
        context = {
            'employee': employee,
            'branch_history': branch_history,
            'error': None
        }
        return render(request, 'partials/branch_history.html', context)
    except Employee.DoesNotExist:
        logger.error(f"Employee not found for ID: {employee_id}")
        return render(request, 'partials/branch_history.html', {
            'error': 'Employee not found',
            'branch_history': []
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching branch history for employee ID: {employee_id}: {str(e)}")
        return render(request, 'partials/branch_history.html', {
            'error': f'Error: {str(e)}',
            'branch_history': []
        }, status=500)


@login_required(login_url='signin')
@require_POST
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def increment_salary(request):
    logger.info(f"Received POST request: {request.POST}, server date: {date.today()}")
    employee_id = request.POST.get('employee_id')
    salary = request.POST.get('salary')
    start_date = request.POST.get('start_date')

    # Validate inputs
    if not all([employee_id, salary, start_date]):
        logger.error(
            f"Missing required fields: employee_id={employee_id}, salary={salary}, start_date={start_date}")
        return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

    try:
        # Convert and validate salary
        try:
            salary = decimal.Decimal(salary)
            if salary <= 0.01:
                logger.error(f"New salary {salary} must be greater than 0.01")
                return JsonResponse({'success': False, 'error': 'New salary must be greater than 0.01'}, status=400)
        except (ValueError, decimal.InvalidOperation):
            logger.error(f"Invalid salary format: {salary}")
            return JsonResponse({'success': False, 'error': 'Invalid salary format'}, status=400)

        # Validate start_date
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            logger.info(f"Parsed start_date: {start_date}")
        except ValueError:
            logger.error(f"Invalid date format: {start_date}")
            return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)

        # Get employee
        try:
            employee = Employee.objects.get(id=employee_id)
            logger.info(f"Found employee: {employee}")
        except ObjectDoesNotExist:
            logger.error(f"Employee not found: id={employee_id}")
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)

        # Validate salary against current salary
        if employee.emp_salary is not None and salary <= employee.emp_salary:
            logger.error(f"New salary {salary} must be greater than current salary {employee.emp_salary}")
            return JsonResponse({'success': False, 'error': 'New salary must be greater than current salary'},
                                status=400)

        # Update employee salary and log to SalaryIncrementHistory
        with transaction.atomic():
            # Check for existing active SalaryIncrementHistory
            current_history = SalaryIncrementHistory.objects.filter(
                employee=employee,
                end_date__isnull=True,
                status='active'
            ).first()

            # Close current history if it exists
            if current_history:
                current_history.end_date = start_date
                current_history.status = 'inactive'
                current_history.save()
                logger.info(f"Updated current SalaryIncrementHistory: {current_history}")

            # Create new SalaryIncrementHistory record
            try:
                SalaryIncrementHistory.objects.create(
                    employee=employee,
                    salary=salary,
                    start_date=start_date,
                    end_date=None,
                )
                logger.info(f"Created new SalaryIncrementHistory for employee: {employee}, salary: {salary}, "
                            f"start_date: {start_date}")
            except IntegrityError as e:
                logger.error(f"IntegrityError creating SalaryIncrementHistory: {str(e)}")
                return JsonResponse({'success': False, 'error': f'Failed to log salary history: {str(e)}'}, status=400)
            except ValidationError as e:
                logger.error(f"ValidationError creating SalaryIncrementHistory: {str(e)}")
                return JsonResponse({'success': False, 'error': f'Invalid data for salary history: {str(e)}'},
                                    status=400)

            # Update employee salary
            employee.emp_salary = salary
            employee.save()
            logger.info(f"Salary incremented successfully for employee: {employee}")

        return JsonResponse({'success': True, 'message': 'Salary incremented successfully'})

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Validation error: {str(e)}'}, status=400)
    except IntegrityError as e:
        logger.error(f"Integrity error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Database error: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required(login_url='signin')
@require_GET
def get_employee_salary_history(request):
    try:
        employee_id = request.GET.get('employee_id')
        if not employee_id:
            logger.error("Missing employee_id parameter")
            return render(request, 'partials/salary_history.html', {
                'error': 'Employee ID is required',
                'salary_history': []
            }, status=400)

        employee = get_object_or_404(Employee, id=employee_id)
        salary_history = SalaryIncrementHistory.objects.filter(employee=employee).order_by('start_date')

        logger.info(f"Fetched {salary_history.count()} salary history records for employee ID: {employee_id}")
        context = {
            'employee': employee,
            'salary_history': salary_history,
            'error': None
        }
        return render(request, 'partials/salary_history.html', context)
    except Employee.DoesNotExist:
        logger.error(f"Employee not found for ID: {employee_id}")
        return render(request, 'partials/salary_history.html', {
            'error': 'Employee not found',
            'salary_history': []
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching salary history for employee ID: {employee_id}: {str(e)}")
        return render(request, 'partials/salary_history.html', {
            'error': f'Error: {str(e)}',
            'salary_history': []
        }, status=500)


@login_required(login_url='signin')
@require_POST
@user_passes_test(is_superuser, login_url='signin', redirect_field_name='redirect_to')
def promote_employee(request):
    logger.info(f"Received POST request: {request.POST}")
    employee_id = request.POST.get('employee_id')
    department_id = request.POST.get('department_id')
    sub_department_id = request.POST.get('sub_department_id')
    category_id = request.POST.get('category_id')
    designation_id = request.POST.get('designation_id')
    start_date = request.POST.get('start_date')

    # Validate required fields
    missing_fields = []
    if not employee_id:
        missing_fields.append('employee_id')
    if not department_id:
        missing_fields.append('department_id')
    if not sub_department_id:
        missing_fields.append('sub_department_id')
    if not category_id:
        missing_fields.append('category_id')
    if not designation_id:
        missing_fields.append('designation_id')
    if not start_date:
        missing_fields.append('start_date')

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        return JsonResponse({'success': False, 'error': error_msg}, status=400)

    try:
        # Validate and parse date
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if start_date > date.today():
            logger.error(f"Future start_date: {start_date}")
            return JsonResponse({'success': False, 'error': 'Promotion date cannot be in the future'}, status=400)

        # Fetch objects
        from hr.models import Employee, Department, SubDepartment, Category, Designation, PromotionHistory
        employee = Employee.objects.get(id=employee_id)
        department = Department.objects.get(id=department_id)
        sub_department = SubDepartment.objects.get(id=sub_department_id)
        category = Category.objects.get(id=category_id)
        designation = Designation.objects.get(id=designation_id)

        # Validate start_date against joining date
        if start_date < employee.emp_joining_date:
            logger.error(
                f"Promotion start_date {start_date} is before joining date {employee.emp_joining_date} for employee {employee.id}")
            return JsonResponse({
                'success': False,
                'error': f'Promotion date cannot be before the employee\'s joining date ({employee.emp_joining_date})'
            }, status=400)

        # Validate hierarchy
        if sub_department.department != department:
            error_msg = 'Sub-department does not belong to the selected department'
            logger.error(error_msg)
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        if category.sub_department != sub_department:
            error_msg = 'Category does not belong to the selected sub-department'
            logger.error(error_msg)
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        if designation.category != category:
            error_msg = 'Designation does not belong to the selected category'
            logger.error(error_msg)
            return JsonResponse({'success': False, 'error': error_msg}, status=400)

        # Check if promotion matches current details
        if (employee.emp_department_id == int(department_id) and
                employee.emp_sub_department_id == int(sub_department_id) and
                employee.emp_category_id == int(category_id) and
                employee.emp_designation_id == int(designation_id)):
            error_msg = 'New promotion must differ from current details'
            logger.error(f"{error_msg} for employee {employee.id}")
            return JsonResponse({'success': False, 'error': error_msg}, status=400)

        with transaction.atomic():
            # Close existing active promotions
            active_promotions = PromotionHistory.objects.select_for_update().filter(
                employee=employee,
                end_date__isnull=True,
                status='active'
            )
            for promotion in active_promotions:
                new_end_date = start_date - timedelta(days=1) if start_date > promotion.start_date else promotion.start_date
                promotion.end_date = new_end_date
                promotion.status = 'inactive'
                promotion.full_clean()
                promotion.save()
                logger.info(f"Closed active promotion {promotion.id} for employee {employee.id} with end_date {new_end_date}")

            # Create new promotion history
            promotion = PromotionHistory(
                employee=employee,
                department=department,
                sub_department=sub_department,
                category=category,
                designation=designation,
                start_date=start_date,
                end_date=None,
                status='active'
            )
            promotion.full_clean()
            promotion.save()
            logger.info(f"Promotion recorded for employee {employee.id}")

        return JsonResponse({'success': True, 'message': 'Promotion recorded successfully'})
    except ObjectDoesNotExist as e:
        logger.error(f"Object not found: {str(e)}")
        return JsonResponse({'success': False, 'error': f'One or more objects not found: {str(e)}'}, status=404)
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Invalid data: {str(e)}'}, status=400)
    except (ValidationError, IntegrityError) as e:
        logger.error(f"Error creating PromotionHistory: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Failed to log promotion history: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required(login_url='signin')
def upgrade_modal(request):
    context = {
        'departments': Department.objects.filter(status='active'),
        'categories': Category.objects.filter(status='active'),
        'subdepartments': SubDepartment.objects.filter(status='active'),
        'designations': Designation.objects.filter(status='active'),
        'branches': Branches.objects.filter(status='active'),
    }

    logger.info(f"Context data: departments={context['departments'].count()}, "
                f"categories={context['categories'].count()}, "
                f"subdepartments={context['subdepartments'].count()}, "
                f"designations={context['designations'].count()}, "
                f"branches={context['branches'].count()}")

    print(f"Subdepartments: {list(context['subdepartments'].values('id', 'sub_department_name'))}")
    print(f"Designations: {list(context['designations'].values('id', 'designation_name'))}")

    return render(request, 'partials/employee_list.html', context)


@login_required(login_url='signin')
@require_GET
def get_promote_history(request):
    try:
        employee_id = request.GET.get('employee_id')
        if not employee_id:
            logger.error("Missing employee_id parameter")
            return render(request, 'partials/promotion_history.html', {
                'error': 'Employee ID is required',
                'promotion_history': []
            }, status=400)

        employee = get_object_or_404(Employee, id=employee_id)
        promotion_history = PromotionHistory.objects.filter(employee=employee).select_related(
            'department', 'sub_department', 'category', 'designation'
        ).order_by('start_date')

        logger.info(f"Fetched {promotion_history.count()} promotion history records for employee ID: {employee_id}")
        context = {
            'employee': employee,
            'promotion_history': promotion_history,
            'error': None
        }
        return render(request, 'partials/promotion_history.html', context)
    except Employee.DoesNotExist:
        logger.error(f"Employee not found for ID: {employee_id}")
        return render(request, 'partials/promotion_history.html', {
            'error': 'Employee not found',
            'promotion_history': []
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching promotion history for employee ID: {employee_id}: {str(e)}")
        return render(request, 'partials/promotion_history.html', {
            'error': f'Error: {str(e)}',
            'promotion_history': []
        }, status=500)


@login_required(login_url='signin')
def list_resigned_employees(request):
    resigned_employees = Employee.objects.filter(emp_status='inactive').order_by('-emp_resigning_date')
    context = {
        'employees': resigned_employees,
        'companies': CompanyName.objects.all(),
        'departments': Department.objects.all(),
        'sub_departments': SubDepartment.objects.all(),
        'categories': Category.objects.all(),
        'designations': Designation.objects.all(),
        'qualifications': Qualification.objects.all(),
        'zones': ZoneofOperations.objects.all(),
        'branches': Branches.objects.all(),
    }
    return render(request, 'partials/resigned_employee_list.html', context)
