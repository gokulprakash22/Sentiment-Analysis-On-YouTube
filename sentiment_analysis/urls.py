from django.urls import path
from . import views

urlpatterns=[
    path('',views.index,name='home'),
    path('home',views.index,name='home'),
    path('report',views.report,name='report'),
    path('more_comments',views.more_comments,name='more_comments'),
    path('csv',views.csv,name='csv'),
    path('pie_chart',views.pie_chart,name='pie_chart')
]