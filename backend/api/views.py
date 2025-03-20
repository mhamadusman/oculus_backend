# views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Doctor
from .serializers import (
    DoctorSignupSerializer, 
    DoctorProfileSerializer, 
    DoctorCompleteSerializer,
    CustomTokenObtainPairSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom view for obtaining JWT tokens
    Uses our custom serializer that includes user data in the response
    """
    serializer_class = CustomTokenObtainPairSerializer

class DoctorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Doctor model - handles all CRUD operations plus custom actions
    """
    queryset = Doctor.objects.all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    def get_permissions(self):
        """
        Define permissions based on the action being performed
        Returns appropriate permission classes
        """
        if self.action == 'signup' or self.action == 'login':
            return [permissions.AllowAny()]
        elif self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        """
        Return different serializers based on the action
        """
        if self.action == 'signup':
            return DoctorSignupSerializer
        elif self.action == 'me' or self.action == 'update_profile':
            return DoctorProfileSerializer
        return DoctorCompleteSerializer
    
    @action(detail=False, methods=['post'])
    def signup(self, request):
        """
        Custom action for user registration
        Creates a new User and Doctor profile
        Returns JWT tokens and user data
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        doctor = Doctor.objects.get(user=user)
        
        profile_picture_url = None
        if doctor.profile_picture:
            profile_picture_url = doctor.profile_picture.url
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'doctor': {
                    'hospital': doctor.hospital,
                    'specialty': doctor.specialty,
                    'role': doctor.role,
                    'license_number': doctor.license_number,
                    'profile_picture': profile_picture_url,
                    'phone_number': doctor.phone_number
                }
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Returns the current user's Doctor profile
        Requires authentication
        """
        doctor = Doctor.objects.get(user=request.user)
        serializer = DoctorCompleteSerializer(doctor)
        return Response(serializer.data)
    


    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        try:
            user = request.user
            print("Received data:", request.data)  # Debug
            print("Received files:", request.FILES)  # Debug files
            
            # Update user fields
            user_data = {
                'first_name': request.data.get('first_name', user.first_name),
                'last_name': request.data.get('last_name', user.last_name),
                'email': request.data.get('email', user.email),
            }
            
            # Filter out None values
            user_data = {k: v for k, v in user_data.items() if v is not None}
            
            # Update user
            if user_data:
                for key, value in user_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.save()
            
            # Update doctor profile
            doctor = Doctor.objects.get(user=user)
            doctor_data = request.data.get('doctor', {})
            
            # Process doctor data
            if doctor_data:
                for key, value in doctor_data.items():
                    if hasattr(doctor, key) and value is not None:
                        setattr(doctor, key, value)
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                doctor.profile_picture = request.FILES['profile_picture']
            
            doctor.save()
            
            # Return complete profile data
            complete_serializer = DoctorCompleteSerializer(doctor)
            return Response(complete_serializer.data)
        
        except Exception as e:
            import traceback
            print("Error in update_profile:", str(e))
            print(traceback.format_exc())
            return Response(
                {"error": str(e)}, 
                status=500
            )
        
        