"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('api-auth/', include('rest_framework.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from support.chat_view import ChatView


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint - health check and documentation"""
    return Response({
        'status': 'running',
        'message': 'AI Customer Support API',
        'version': '1.0.0',
        'endpoints': {
            'chat': '/api/chat/',
            'auth': '/api/accounts/',
            'documents': '/api/support/documents/',
            'conversations': '/api/support/conversations/',
            'admin': '/admin/',
        },
        'quick_start': {
            '1_register': 'POST /api/accounts/register/register/',
            '2_login': 'POST /api/accounts/token/',
            '3_upload_document': 'POST /api/support/documents/',
            '4_get_chunks': 'GET /api/support/documents/{id}/chunks/',
            '5_chat': 'POST /api/chat/',
        }
    })


urlpatterns = [
    path('', api_root, name='api_root'),
    path('admin/', admin.site.urls),
    path('api/chat/', ChatView.as_view(), name='chat'),
    path('api/support/', include('support.urls')),
    path('api/accounts/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
