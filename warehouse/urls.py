from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/create/', views.product_create, name='product_create'),
    path('product/<int:pk>/update/', views.product_update, name='product_update'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),

    path('movement/create/', views.stock_movement_create, name='stock_movement_create'),

    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/generate/', views.invoice_generate, name='invoice_generate'),
    path('invoice/<int:pk>/download/', views.invoice_download_pdf, name='invoice_download_pdf'),

    path('api/product-search/', views.api_product_search, name='api_product_search'),
    path('api/product-stock/<int:product_id>/', views.api_product_stock, name='api_product_stock'),
]