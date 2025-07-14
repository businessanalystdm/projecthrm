# hrm/urls.py
"""
URL configuration for hrm project.
"""

from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from hr.views import IndexView  # Import IndexView directly
from hr import views as hr_views
from accounts import views as accounts_views
from mobile_punchin import views as mobile_punchin_views

app_name = 'hrm'  # Single app_name

urlpatterns = [
    path('admin/', admin.site.urls),
    path('index', IndexView.as_view(), name='index'),

    # CompanyName URLs
    path('company-name/add/', hr_views.add_company_name, name='add_company_name'),
    path('company-name/list/', hr_views.company_name_list, name='company_name_list'),
    path('company-name/delete/<int:id>/', hr_views.delete_company_name, name='delete_company_name'),
    path('company-name/update/<int:id>/', hr_views.update_company_name, name='update_company_name'),
    path('get_companies/', hr_views.get_companies, name='get_companies'),

    # Department URLs
    path('department/add/', hr_views.add_department, name='add_department'),
    path('department/update/<int:id>/', hr_views.update_department, name='update_department'),
    path('department/delete/<int:id>/', hr_views.delete_department, name='delete_department'),
    path('department/list/', hr_views.department_list, name='department_list'),
    path('department/by-company/<int:company_id>/', hr_views.get_departments_by_company,
         name='get_departments_by_company'),

    # SubDepartment URLs
    path('sub-department/add/', hr_views.add_subdepartment, name='add_subdepartment'),
    path('sub-department/update/<int:id>/', hr_views.update_subdepartment, name='update_subdepartment'),
    path('sub-department/delete/<int:id>/', hr_views.delete_subdepartment, name='delete_subdepartment'),
    path('sub-department/list/', hr_views.subdepartment_list, name='sub_department_list'),
    path('sub-department/by-department/<int:department_id>/', hr_views.get_subdepartments_by_department,
         name='get_subdepartments_by_department'),

    # Category URLs
    path('category/add/', hr_views.add_category, name='add_category'),
    path('category/list/', hr_views.category_list, name='category_list'),
    path('category/update/<int:id>/', hr_views.update_category, name='update_category'),
    path('category/delete/<int:id>/', hr_views.delete_category, name='delete_category'),
    path('category/by-subdepartment/<int:subdepartment_id>/', hr_views.get_categories_by_subdepartment,
         name='get_categories_by_subdepartment'),

    # Designation URLs
    path('designation/list/', hr_views.designation_list, name='designation_list'),
    path('designation/add/', hr_views.add_designation, name='add_designation'),
    path('designation/update/<int:id>/', hr_views.update_designation, name='update_designation'),
    path('designation/delete/<int:id>/', hr_views.delete_designation, name='delete_designation'),
    path('designation/by-category/<int:category_id>/', hr_views.get_designations_by_category,
         name='get_designations_by_category'),

    # Qualification URLs
    path('qualification/add/', hr_views.add_qualification, name='add_qualification'),
    path('qualification/update/<int:id>/', hr_views.update_qualification, name='update_qualification'),
    path('qualification/delete/<int:id>/', hr_views.delete_qualification, name='delete_qualification'),
    path('qualification/list/', hr_views.qualification_list, name='qualification_list'),

    # Zone URLs
    path('zone/list/', hr_views.zone_list, name='zone_list'),
    path('zone/add/', hr_views.add_zone, name='add_zone'),
    path('zone/update/<int:id>/', hr_views.update_zone, name='update_zone'),
    path('zone/delete/<int:id>/', hr_views.delete_zone, name='delete_zone'),

    # Branches URLs
    path('branches/add/', hr_views.add_branch, name='add_branch'),
    path('branches/update/<int:id>/', hr_views.update_branch, name='update_branch'),
    path('branches/delete/<int:id>/', hr_views.delete_branch, name='delete_branch'),
    path('branches/list/', hr_views.branches_list, name='branches_list'),

    # Employee URLs
    path('list-employees/', hr_views.list_employees, name='employee_list'),
    path('employee/add/', hr_views.add_employee, name='add_employee'),
    path('employee/form/<int:employee_id>/', hr_views.employee_form, name='employee_form'),
    path('employee/delete/<int:employee_id>/', hr_views.delete_employee, name='delete_employee'),
    path('employee/details/<str:emp_id>/', hr_views.employee_details, name='employee_details'),
    path('get_employee_details/', hr_views.get_employee_details, name='get_employee_details'),
    path('get_employee_for_edit/<int:employee_id>/', hr_views.get_employee_for_edit, name='get_employee_for_edit'),
    path('get_employee_details_for_upgrade/', hr_views.get_employee_details_for_upgrade,
         name='get_employee_details_for_upgrade'),
    path('api/employees/', hr_views.employee_list_api, name='employee_list_api'),
    path('resign_employee/', hr_views.resign_employee, name='resign_employee'),
    path('list-resigned-employees/', hr_views.list_resigned_employees, name='list_resigned_employees'),
    path('list-employees-with-history/', hr_views.list_employees_with_history, name='list_employees_with_history'),
    path('get-employee-branch-history/', hr_views.get_employee_branch_history, name='get_employee_branch_history'),
    path('transfer_branch/', hr_views.transfer_branch, name='transfer_branch'),
    path('increment_salary/', hr_views.increment_salary, name='increment_salary'),
    path('get-employee-salary-history/', hr_views.get_employee_salary_history, name='get_employee_salary_history'),
    path('promote_employee/', hr_views.promote_employee, name='promote_employee'),
    path('promotion-history/', hr_views.get_promote_history, name='promotion_history'),

    # Asset URLs
    path('assets/list/', hr_views.asset_list, name='asset_list'),
    path('assets/assign/', hr_views.assign_asset, name='assign_asset'),
    path('assets/remove/', hr_views.remove_asset, name='remove_asset'),
    path('assets/modal/', hr_views.assets_modal, name='assets_modal'),
    path('assets/add/', hr_views.add_asset, name='add_asset'),
    path('assets/delete/', hr_views.delete_asset, name='delete_asset'),
    path('get_employee_assets/', hr_views.get_employee_assets, name='get_employee_assets'),

    # Skill URLs
    path('skills/list/', hr_views.skill_list, name='skill_list'),

    # Accounts URLs
    path('signup/', accounts_views.signup_view, name='signup'),
    path('', accounts_views.signin_view, name='signin'),
    path('logout/', accounts_views.logout_view, name='logout'),

    path('create-mobile-punchin-id/', mobile_punchin_views.create_mobile_punchin_id, name='create_mobile_punchin_id'),
    path('list-mobile-punchin-ids/', mobile_punchin_views.list_mobile_punchin_ids, name='list_mobile_punchin_ids'),

    path('punch-login/', mobile_punchin_views.login_page, name='login_page'),
    path('api/login/', mobile_punchin_views.login_mobile_punchin, name='login_mobile_punchin'),
    path('main/', mobile_punchin_views.mainpage, name='mainpage'),
    path('api/punch-in/', mobile_punchin_views.punch_in, name='punch_in'),
    path('api/punch-out/', mobile_punchin_views.punch_out, name='punch_out'),
    path('logout/', mobile_punchin_views.logout_view, name='logout'),
    path('list-punch-records/', mobile_punchin_views.list_punch_records, name='list_punch_records'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL,
                                                                                          document_root=settings.STATIC_ROOT)
