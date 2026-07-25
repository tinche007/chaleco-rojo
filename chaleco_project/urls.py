from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from chaleco_app.views import (
    crear_informe_view, 
    historial_informes_view, 
    eliminar_informe_view,
    inicio_view, 
    exportar_pdf_view,
    lista_clientes_view,  
    alta_cliente_view,   
    baja_cliente_view,
    detalle_cliente_view,
    reactivar_cliente_view,
    asistente_ia_view,
    lista_auditorias,
    realizar_auditoria,
    resultado_auditoria,
    auditoria_express,
    resultado_auditoria_express,  # ✅ YA ESTÁ IMPORTADA
    dashboard_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', inicio_view, name='inicio'),
    path('crear_informe/', crear_informe_view, name='crear_informe'),
    path('historial/', historial_informes_view, name='historial_informes'),
    path('historial/eliminar/<int:informe_id>/', eliminar_informe_view, name='eliminar_informe'),
    path('informe/<int:informe_id>/pdf/', exportar_pdf_view, name='exportar_pdf'),
    path('clientes/', lista_clientes_view, name='lista_clientes'),
    path('clientes/nuevo/', alta_cliente_view, name='alta_cliente'),
    path('clientes/baja/<int:cliente_id>/', baja_cliente_view, name='baja_cliente'),
    path('clientes/reactivar/<int:cliente_id>/', reactivar_cliente_view, name='reactivar_cliente'),
    path('clientes/<int:cliente_id>/', detalle_cliente_view, name='detalle_cliente'),
    path('asistente-ia/', asistente_ia_view, name='asistente_ia'),
    path('auditorias/', lista_auditorias, name='lista_auditorias'),
    path('auditorias/<int:cliente_id>/', realizar_auditoria, name='realizar_auditoria'),
    path('auditorias/<int:cliente_id>/resultado/', resultado_auditoria, name='resultado_auditoria'),
    path('auditorias/<int:cliente_id>/express/', auditoria_express, name='auditoria_express'),
    path('auditorias/<int:cliente_id>/express/resultado/', resultado_auditoria_express, name='resultado_auditoria_express'),  # ✅ SIN views.
    path('dashboard/', dashboard_view, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)