from django.urls import path
from . import views

app_name = 'feedback_widget'

urlpatterns = [
    path('submit/', views.submit, name='submit'),
    path('admin/', views.admin_list, name='admin_list'),
    path('admin/<int:pk>/', views.admin_detail, name='admin_detail'),
    path('admin/<int:pk>/delete/', views.admin_delete, name='admin_delete'),
]
