from django.urls import path
from . import views

urlpatterns = [
    # Fee schedule
    path('forms/', views.CourtFormListView.as_view(), name='court-forms'),

    # Case CRUD
    path('', views.CaseListCreateView.as_view(), name='case-list'),
    path('<uuid:id>/', views.CaseDetailView.as_view(), name='case-detail'),

    # Lawyer actions
    path('<uuid:id>/submit/', views.CaseSubmitView.as_view(), name='case-submit'),
    path('<uuid:id>/resubmit/', views.CaseResubmitView.as_view(), name='case-resubmit'),

    # Accounts workflow
    path('accounts/queue/', views.AccountsQueueView.as_view(), name='accounts-queue'),
    path('<uuid:id>/accounts/review/', views.AccountsReviewView.as_view(), name='accounts-review'),

    # Registrar workflow
    path('registrar/queue/', views.RegistrarQueueView.as_view(), name='registrar-queue'),
    path('<uuid:id>/registrar/review/', views.RegistrarReviewView.as_view(), name='registrar-review'),
]
