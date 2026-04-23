from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.AuditLogListView.as_view(), name='audit-log-list'),
    path('cases/<uuid:case_id>/', views.CaseAuditLogView.as_view(), name='audit-case-log'),
]
