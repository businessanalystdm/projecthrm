from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import SignInForm, SignUpForm
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

@never_cache
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Assuming password validation (e.g., confirm_password matches password)
            if form.cleaned_data['password'] == form.cleaned_data['confirm_password']:
                user.set_password(form.cleaned_data['password'])
                user.save()
                login(request, user)  # Optional: Log in the user after signup
                messages.success(request, 'Account created successfully!')
                return redirect('signup')  # Redirect back to signup page
            else:
                form.add_error('confirm_password', 'Passwords do not match.')
        # If form is invalid, re-render with errors
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

@never_cache
def signin_view(request):
    if request.method == 'POST':
        form = SignInForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = SignInForm()
    return render(request, 'accounts/signin.html', {'form': form})

@never_cache
@require_POST
def logout_view(request):
    if request.method == 'POST':
        logout(request)  # Log out the user
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
