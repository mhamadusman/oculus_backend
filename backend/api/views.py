from django.core.files import File
import os
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Doctor, OCTImage, AnalysisResult, Review
from .serializers import (
    DoctorSignupSerializer, DoctorProfileSerializer, DoctorCompleteSerializer,
    CustomTokenObtainPairSerializer, OCTImageSerializer, OCTImageCreateSerializer,
    OCTImageDetailSerializer, AnalysisResultSerializer, AnalysisResultDetailSerializer,
     ReviewSerializer, ReviewCreateSerializer, PublicReviewSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, 'doctor'):
            return obj.doctor.user == request.user
        elif hasattr(obj, 'oct_image'):
            return obj.oct_image.doctor.user == request.user
        elif hasattr(obj, 'analysis_result'):
            return obj.analysis_result.oct_image.doctor.user == request.user
        return False

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    def get_permissions(self):
        if self.action == 'signup' or self.action == 'login':
            return [permissions.AllowAny()]
        elif self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'signup':
            return DoctorSignupSerializer
        elif self.action == 'me' or self.action == 'update_profile':
            return DoctorProfileSerializer
        return DoctorCompleteSerializer
    
    @action(detail=False, methods=['post'])
    def signup(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        doctor = Doctor.objects.get(user=user)
        profile_picture_url = doctor.profile_picture.url if doctor.profile_picture else None
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
        doctor = Doctor.objects.get(user=request.user)
        serializer = DoctorCompleteSerializer(doctor)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        user = request.user
        doctor = Doctor.objects.get(user=user)
        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)



def run_ai_analysis(image_path):
    # For testing, simulate AI analysis using the uploaded image as the processed image
    return {
        'category': 'normal',
        'text': 'No abnormalities detected.',
        'image_path': image_path  # Return the path instead of a File object
    }
class OCTImageViewSet(viewsets.ModelViewSet):
    queryset = OCTImage.objects.all()
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['custom_id']
    ordering_fields = ['upload_date']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OCTImageCreateSerializer
        elif self.action == 'retrieve':
            return OCTImageDetailSerializer
        return OCTImageSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            doctor = Doctor.objects.get(user=self.request.user)
            return OCTImage.objects.filter(doctor=doctor)
        return OCTImage.objects.none()
    
    # def perform_create(self, serializer):
    #     doctor = Doctor.objects.get(user=self.request.user)
    #     oct_image = serializer.save(doctor=doctor)
    #     # Call AI model simulation and create AnalysisResult
    #     ai_result = run_ai_analysis(oct_image.image_file.path)
    #     analysis_result = AnalysisResult.objects.create(
    #         oct_image=oct_image,
    #         classification=ai_result['category'],
    #         findings=ai_result['text'],
    #     )
    #     if ai_result['image_path']:
    #         # Open the file explicitly and save it
    #         with open(ai_result['image_path'], 'rb') as f:
    #             analysis_result.analysis_image.save(
    #                 f"processed_{oct_image.id}.jpg",
    #                 File(f),
    #                 save=True
    #             )

    def perform_create(self, serializer):
        doctor = Doctor.objects.get(user=self.request.user)
        oct_image = serializer.save(doctor=doctor)
        
        # Call AI model simulation and create AnalysisResult
        ai_result = run_ai_analysis(oct_image.image_file.path)
        analysis_result = AnalysisResult.objects.create(
            oct_image=oct_image,
            classification=ai_result['category'],
            findings=ai_result['text'],
        )

        if ai_result.get('image_path'):
            # Open the file explicitly and save it
            with open(ai_result['image_path'], 'rb') as f:
                analysis_result.analysis_image.save(
                    f"processed_{oct_image.id}.jpg",
                    File(f),
                    save=True
                )

        # Ensure the response contains `id`
        self.response = OCTImageDetailSerializer(oct_image).data

# Placeholder for AI function


class AnalysisResultViewSet(viewsets.ModelViewSet):
    queryset = AnalysisResult.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['classification']
    ordering_fields = ['analysis_date']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AnalysisResultDetailSerializer
        return AnalysisResultSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            doctor = Doctor.objects.get(user=self.request.user)
            return AnalysisResult.objects.filter(oct_image__doctor=doctor)
        return AnalysisResult.objects.none()

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-review_date')
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['analysis_result']
    ordering_fields = ['review_date', 'rating']
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        doctor = self.request.user.doctor
        serializer.save(doctor=doctor)

    def perform_update(self, serializer):
        serializer.save()