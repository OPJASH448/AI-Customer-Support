from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'support'

router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'escalations', views.EscalationTicketViewSet, basename='escalation')

urlpatterns = [
    path('', include(router.urls)),
    path('rag/ask/', views.RAGAskView.as_view(), name='rag-ask'),
    path('tickets/', views.TicketListView.as_view(), name='ticket-list'),
    path('tickets/<int:pk>/resolve/', views.TicketResolveView.as_view(), name='ticket-resolve'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
]
