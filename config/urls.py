from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from support.chat_view import ChatView
from support.views import TicketListView, TicketResolveView, AnalyticsView


@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
def api_root(request):
    """API root — returns JSON for API clients, redirects browsers to the UI."""
    # DRF API clients (Accept: application/json) get JSON
    # Browser requests get redirected to the frontend
    accept = request.headers.get('Accept', '')
    if 'text/html' in accept and 'application/json' not in accept:
        return redirect('/login/')
    return Response({
        'status': 'running',
        'message': 'AI Customer Support API',
        'version': '1.0.0',
        'ui': 'http://localhost:8000/chat/',
        'endpoints': {
            'chat_ui':     '/chat/',
            'dashboard':   '/dashboard/',
            'documents':   '/documents/',
            'api_chat':    '/api/chat/',
            'tickets':     '/api/tickets/',
            'analytics':   '/api/analytics/',
            'auth':        '/api/accounts/',
            'documents_api': '/api/support/documents/',
            'admin':       '/admin/',
        },
    })


urlpatterns = [
    # ── Root ────────────────────────────────────────────────────────
    path('', api_root, name='api_root'),

    # ── Frontend UI (session-auth Django templates) ──────────────────
    path('', include('frontend.urls', namespace='frontend')),

    # ── Admin ────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── REST API ─────────────────────────────────────────────────────
    path('api/chat/', ChatView.as_view(), name='chat'),
    path('api/tickets/', TicketListView.as_view(), name='ticket-list'),
    path('api/tickets/<int:pk>/resolve/', TicketResolveView.as_view(), name='ticket-resolve'),
    path('api/analytics/', AnalyticsView.as_view(), name='analytics'),
    path('api/support/', include('support.urls')),
    path('api/accounts/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
