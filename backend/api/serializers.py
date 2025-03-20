# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Doctor
from django.db.utils import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model
    Handles conversion between User model instances and Python data types
    """
    class Meta:
        # Specify which model this serializer is for
        model = User
        # List of fields to include in the serialized output
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        # Fields that are read-only and cannot be modified via the serializer
        read_only_fields = ('id',)

class DoctorProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the Doctor model
    Handles only the Doctor-specific fields (not User fields)
    """
    class Meta:
        model = Doctor
        # Only include Doctor model fields, not the related User fields
        # UPDATED: Added profile_picture to the list of fields
        fields = ('hospital', 'specialty', 'role', 'license_number', 'profile_picture' , 'phone_number')

class DoctorSignupSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    def create(self, validated_data):
        try:
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', '')
            )
            Doctor.objects.create(user=user)
            return user
        except IntegrityError as e:
            if 'username' in str(e):
                raise ValidationError({"username": "This username is already taken."})
            elif 'email' in str(e):
                raise ValidationError({"email": "This email is already in use."})
            else:
                raise ValidationError("An error occurred during signup.")

class DoctorCompleteSerializer(serializers.ModelSerializer):
    """
    Serializer that combines User and Doctor data in a nested structure
    """
    # Nested serializer - includes all User fields in the response
    user = UserSerializer()
    
    class Meta:
        model = Doctor
        # Include the nested user serializer and all Doctor fields
        # UPDATED: Added profile_picture to the list of fields
        fields = ('user', 'hospital', 'specialty', 'role', 'license_number', 'profile_picture' , 'phone_number')

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user data in the response
    Extends the standard JWT token serializer
    """
    def validate(self, attrs):
        # Call the parent validate method to authenticate user and create tokens
        data = super().validate(attrs)
        
        # Get the authenticated user (set by parent class)
        user = self.user
        try:
            # Try to get the associated Doctor profile
            doctor = Doctor.objects.get(user=user)
            
            # NEW: Get the profile picture URL if it exists
            profile_picture_url = None
            if doctor.profile_picture:
                profile_picture_url = doctor.profile_picture.url
            
            # Add user and doctor data to the response
            data['user'] = {
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
                    # NEW: Include profile picture URL in the response
                    'profile_picture': profile_picture_url
                }
            }
        except Doctor.DoesNotExist:
            # If the Doctor profile doesn't exist, create one
            Doctor.objects.create(user=user)
            # Add user data with empty doctor fields
            data['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'doctor': {
                    'hospital': '',
                    'specialty': '',
                    'role': 'general',
                    'license_number': '',
                    # NEW: Set profile picture to None for new profiles
                    'profile_picture': None
                }
            }
            
        return data