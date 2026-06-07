from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from users.models import User, Profile, Achievement
from users.serializers import UserSerializer, RegisterSerializer, ProfileSerializer

# --- DRF REST API VIEWS ---

class APIRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIUserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Update profile subfield
            if 'profile' in request.data:
                profile_data = request.data['profile']
                profile_serializer = ProfileSerializer(user.profile, data=profile_data, partial=True)
                if profile_serializer.is_valid():
                    profile_serializer.save()
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- DJANGO HTML + HTMX TEMPLATE VIEWS ---

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                
                # Check for HTMX redirect headers
                if request.headers.get('HX-Request'):
                    response = HttpResponse()
                    response['HX-Redirect'] = '/dashboard/'
                    return response
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
            
        if request.headers.get('HX-Request'):
            return render(request, 'partials/messages.html')

    form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Hand-roll registration parameter extraction for simple template post
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', User.CITIZEN)
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        
        # Simple validation
        if not username or not password or not email:
            messages.error(request, "Please fill in all required fields.")
            if request.headers.get('HX-Request'):
                return render(request, 'partials/messages.html')
            return render(request, 'signup.html')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            if request.headers.get('HX-Request'):
                return render(request, 'partials/messages.html')
            return render(request, 'signup.html')

        # Enforce password validation policy
        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as e:
            messages.error(request, ", ".join(e.messages))
            if request.headers.get('HX-Request'):
                return render(request, 'partials/messages.html')
            return render(request, 'signup.html')

        try:
            # Hash password and create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role
            )
            profile, created = Profile.objects.get_or_create(user=user)
            if phone:
                profile.phone = phone
            if address:
                profile.address = address
            profile.save()
            
            # Authenticate and login
            login(request, user)
            messages.success(request, "Account created successfully!")
            
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = '/dashboard/'
                return response
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Error: {e}")
            if request.headers.get('HX-Request'):
                return render(request, 'partials/messages.html')
            
    return render(request, 'signup.html')


def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('landing')


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        user.email = request.POST.get('email', user.email)
        profile.bio = request.POST.get('bio', profile.bio)
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        if phone is not None:
            profile.phone = phone
        if address is not None:
            profile.address = address
            
        user.save()
        profile.save()
        messages.success(request, "Profile updated successfully!")
        
        if request.headers.get('HX-Request'):
            return render(request, 'partials/messages.html')
            
    return render(request, 'profile.html', {'user': user, 'profile': profile})


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    reset_link = None
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                path = f"/forgot-password/reset/{uidb64}/{token}/"
                reset_link = request.build_absolute_uri(path)
                messages.success(request, "Password reset link generated successfully.")
            except User.DoesNotExist:
                messages.error(request, "No account exists with this email address.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
                
    return render(request, 'forgot_password.html', {'reset_link': reset_link})


def reset_password_confirm_view(request, uidb64, token):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            if not password or not confirm_password:
                messages.error(request, "Please enter all fields.")
                return render(request, 'reset_password_confirm.html')
                
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'reset_password_confirm.html')
                
            try:
                validate_password(password, user=user)
            except ValidationError as e:
                messages.error(request, ", ".join(e.messages))
                return render(request, 'reset_password_confirm.html')
                
            try:
                user.set_password(password)
                user.save()
                messages.success(request, "Your password has been reset successfully. Please sign in.")
                
                if request.headers.get('HX-Request'):
                    response = HttpResponse()
                    response['HX-Redirect'] = '/login/'
                    return response
                return redirect('login')
            except Exception as e:
                messages.error(request, f"Error: {e}")
                
        return render(request, 'reset_password_confirm.html')
    else:
        messages.error(request, "The password reset link is invalid or has expired.")
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = '/forgot-password/'
            return response
        return redirect('forgot_password')
