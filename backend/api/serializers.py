from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Doctor, OCTImage, AnalysisResult, Review
from django.db.utils import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import OCTImage, AnalysisResult, Doctor



# Keep all Doctor-related serializers exactly as they were
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ('hospital', 'specialty', 'role', 'license_number', 'profile_picture', 'phone_number')

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
        except Exception as e:
            raise ValidationError({"error": str(e)})

class DoctorCompleteSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Doctor
        fields = ('user', 'hospital', 'specialty', 'role', 'license_number', 'profile_picture', 'phone_number')

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        doctor = Doctor.objects.get(user=user)
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
                'profile_picture': doctor.profile_picture.url if doctor.profile_picture else None,
                'phone_number': doctor.phone_number
            }
        }
        return data
class OCTImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCTImage
        fields = ('id', 'doctor', 'image_file', 'upload_date', 'custom_id')
        read_only_fields = ('id', 'upload_date')

class OCTImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCTImage
        fields = ('image_file', 'custom_id')
    
    def create(self, validated_data):
        doctor = self.context['request'].user.doctor
        validated_data['doctor'] = doctor
        return super().create(validated_data)


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = ('id', 'oct_image', 'classification', 'findings', 'analysis_image', 'analysis_date')
        read_only_fields = ('id', 'analysis_date')
        
class OCTImageDetailSerializer(serializers.ModelSerializer):
    doctor = DoctorCompleteSerializer(read_only=True)
    analysis_result = AnalysisResultSerializer(read_only=True)
    
    class Meta:
        model = OCTImage
        fields = ('id', 'doctor', 'image_file', 'upload_date', 'custom_id', 'analysis_result')
        read_only_fields = ('id', 'upload_date', 'doctor')


class AnalysisResultDetailSerializer(serializers.ModelSerializer):
    oct_image = OCTImageDetailSerializer(read_only=True)
    
    class Meta:
        model = AnalysisResult
        fields = ('id', 'oct_image', 'classification', 'findings', 'analysis_image', 'analysis_date')
        read_only_fields = ('id', 'analysis_date', 'oct_image')

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'analysis_result', 'doctor', 'rating', 'comments', 'review_date')
        read_only_fields = ('id', 'review_date')

class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('analysis_result', 'rating', 'comments')
    
    def create(self, validated_data):
        doctor = self.context['request'].user.doctor
        validated_data['doctor'] = doctor
        existing_review = Review.objects.filter(analysis_result=validated_data['analysis_result']).exists()
        if existing_review:
            raise ValidationError({"analysis_result": "A review already exists for this analysis result."})
        return super().create(validated_data)

class ReviewDetailSerializer(serializers.ModelSerializer):
    analysis_result = AnalysisResultDetailSerializer(read_only=True)
    doctor = DoctorCompleteSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ('id', 'analysis_result', 'doctor', 'rating', 'comments', 'review_date')
        read_only_fields = ('id', 'review_date', 'analysis_result', 'doctor')