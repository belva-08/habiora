from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # ===== LISTE ET DÉTAIL =====
    path('', views.property_list, name='list'),
    path('map/', views.property_map, name='map'),
    path('search-ajax/', views.property_search_ajax, name='search_ajax'),
    path('<int:property_id>/', views.property_detail, name='detail'),
    
    # ===== FAVORI =====
    path('<int:property_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    
    # ===== SIGNALEMENT =====
    path('<int:property_id>/report/', views.report_property, name='report'),
]