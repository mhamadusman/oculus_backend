# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorViewSet, CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
# NEW: Import settings and static for serving media files
from django.conf import settings
from django.conf.urls.static import static

# Create a router for automatic URL routing for the viewset
router = DefaultRouter()
# Register the DoctorViewSet with the 'doctors' prefix
router.register(r'doctors', DoctorViewSet, basename='doctor')

# Define URL patterns
urlpatterns = [
    # Include all URLs from the router
    path('', include(router.urls)),
    # JWT token endpoints
    # Change these lines in your app's urls.py
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# NEW: Add media URL configuration for development environment
# This allows Django to serve user-uploaded files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)