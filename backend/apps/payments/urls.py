from django.urls import path
from . import views

urlpatterns = [
    path('cases/<uuid:case_id>/initiate/', views.PaymentInitiateView.as_view(), name='payment-initiate'),
    path('cases/<uuid:case_id>/', views.PaymentStatusView.as_view(), name='payment-status'),
    path('callback/', views.MUSUCallbackView.as_view(), name='payment-callback'),
    path('mock-confirm/', views.MockPaymentConfirmView.as_view(), name='payment-mock-confirm'),
]
