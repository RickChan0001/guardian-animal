from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tutores import views as tutor_views
from veterinarios import views as vet_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', tutor_views.home, name='home'),
    path('login/', tutor_views.login_view, name='login'),
    path('logout/', tutor_views.logout_view, name='logout'),
    path('tutores/', include(('tutores.urls', 'tutores'), namespace='tutores')),
    path('veterinarios/', include(('veterinarios.urls', 'veterinarios'), namespace='veterinarios')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
