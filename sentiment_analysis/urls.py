from django.urls import path
from . import views

urlpatterns=[
    path('',views.index,name='home'),
    path('pie',views.pie,name='pie'),
    path('search',views.search,name='search'),


]