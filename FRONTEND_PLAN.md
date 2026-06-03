# AI Customer Support Frontend — Full Implementation Plan

## Files to Create / Modify

### NEW: templates/
- templates/base.html          — Tailwind CDN + HTMX CDN, nav sidebar
- templates/chat.html          — Chat widget page (floating button + slide-up panel)
- templates/dashboard.html     — Agent dashboard (tickets, stats, sidebar)
- templates/documents.html     — Document manager (upload, list, status)
- templates/login.html         — JWT login page (session-based for frontend)

### NEW: frontend/views.py     — Django template views (not API)
### MODIFY: config/urls.py     — Add frontend URL routes
### MODIFY: config/settings/production.py — Fix SECURE_CONTENT_SECURITY_POLICY (not a real Django setting), remove it
### MODIFY: render.yaml        — Add GEMINI_API_KEY env var reference

## Endpoint Mapping (what HTMX calls)
- POST /api/chat/           { user_message, conversation_id } → JSON
- GET  /api/tickets/        → JSON list
- PATCH /api/tickets/{id}/resolve/ → JSON
- GET  /api/analytics/      → JSON
- GET  /api/support/documents/ → JSON list
- POST /api/support/documents/ → multipart upload
- DELETE /api/support/documents/{id}/ → 204

## Auth Strategy
- Frontend uses sessionauth for simplicity (login form posts to /auth/login/)
- Backend already has JWT — add SessionAuthentication alongside JWT in REST_FRAMEWORK
- Django login view at /login/ sets session cookie, HTMX calls benefit from session
