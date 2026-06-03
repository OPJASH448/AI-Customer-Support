from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('',         views.chat_view,      name='chat'),
    path('chat/',    views.chat_view,      name='chat'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('documents/', views.documents_view, name='documents'),
    path('login/',   views.login_view,    name='login'),
    path('logout/',  views.logout_view,   name='logout'),
]
