from django.conf import settings 
from django.conf.urls.static import static 
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('not-admin/', admin.site.urls),

    # User Management
    path("accounts/", include("allauth.urls")),

    # Local apps 
    path("", include("podcasts.urls")),
] + static(
settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
) 
