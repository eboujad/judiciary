from django.urls import path
from . import views

urlpatterns = [
    path('cases/<uuid:case_id>/', views.DocumentListView.as_view(), name='document-list'),
    path('cases/<uuid:case_id>/upload/', views.DocumentUploadView.as_view(), name='document-upload'),
    path('<uuid:doc_id>/verify/', views.DocumentVerifyView.as_view(), name='document-verify'),
    path('<uuid:doc_id>/', views.DocumentDeleteView.as_view(), name='document-delete'),
]
