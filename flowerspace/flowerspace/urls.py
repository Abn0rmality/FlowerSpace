from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('superdupersecretadminpanel/', admin.site.urls),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('shop/', include('onlineshop.urls', namespace='shop')),
    path('api/', include('api.urls')),
    path('', include('home.urls', namespace='home')),
] 

if settings.DEBUG:
    urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
