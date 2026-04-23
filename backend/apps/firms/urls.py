from django.urls import path
from . import views

urlpatterns = [
    path('', views.FirmListCreateView.as_view(), name='firm-list'),
    path('mine/', views.MyFirmView.as_view(), name='firm-mine'),
    path('<uuid:id>/', views.FirmDetailView.as_view(), name='firm-detail'),
    path('<uuid:id>/approve/', views.FirmApproveView.as_view(), name='firm-approve'),
    path('<uuid:firm_id>/lawyers/', views.FirmLawyersView.as_view(), name='firm-lawyers'),
]
