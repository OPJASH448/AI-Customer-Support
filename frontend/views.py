"""
Frontend views — renders Django templates for the web UI.
All data fetching is done client-side via JavaScript + the existing REST API.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User

from support.models import Conversation


@require_http_methods(['GET', 'POST'])
def login_view(request):
    """Login page — session-based auth for the frontend."""
    if request.user.is_authenticated:
        return redirect('frontend:chat')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'frontend:chat')
            return redirect(next_url)
        error = 'Invalid username or password. Please try again.'

    features = [
        ('🧠', 'RAG Vector Search'),
        ('⚡', 'Gemini 2.0 Flash'),
        ('🔒', 'JWT Secured'),
    ]
    return render(request, 'login.html', {'error': error, 'features': features})


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    """Log out and redirect to login."""
    logout(request)
    return redirect('frontend:login')


@login_required(login_url='/login/')
def chat_view(request):
    """Main chat interface with conversation history sidebar."""
    conversations = Conversation.objects.filter(
        user=request.user
    ).order_by('-updated_at')[:20]

    current_conv_id = None  # No specific conversation selected by default

    return render(request, 'chat.html', {
        'conversations': conversations,
        'current_conv_id': current_conv_id,
    })


@login_required(login_url='/login/')
def dashboard_view(request):
    """Agent dashboard — tickets and analytics (data loaded client-side)."""
    return render(request, 'dashboard.html', {})


@login_required(login_url='/login/')
def documents_view(request):
    """Document manager — upload and list (data loaded client-side)."""
    return render(request, 'documents.html', {})
