from django.urls import path
from . import views

urlpatterns=[
    path('',views.index,name='home'),
    path('pie_chart',views.pie_chart,name='pie_chart'),
    path('report',views.report,name='report'),
    path('csv',views.csv,name='csv'),
    path('home',views.index,name='home'),




]