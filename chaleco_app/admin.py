from django.contrib import admin
from .models import (
    Organizacion, PerfilUsuario, ClienteEmpresa, 
    InformeVisita, HallazgoRiesgo,
    CategoriaPregunta, PreguntaAuditoria, Auditoria, RespuestaAuditoria
)

# ==========================================
# MODELOS EXISTENTES
# ==========================================

@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'fecha_creacion')
    search_fields = ('nombre',)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organizacion', 'es_administrador')
    list_filter = ('organizacion', 'es_administrador')
    search_fields = ('user__username', 'user__email')


@admin.register(ClienteEmpresa)
class ClienteEmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_fantasia', 'razon_social', 'cuit', 'organizacion', 'activo')
    list_filter = ('organizacion', 'activo')
    search_fields = ('nombre_fantasia', 'razon_social', 'cuit')


@admin.register(InformeVisita)
class InformeVisitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha_visita', 'inspector', 'organizacion')
    list_filter = ('organizacion', 'fecha_visita')
    search_fields = ('cliente__nombre_fantasia', 'establecimiento_ocasional')


@admin.register(HallazgoRiesgo)
class HallazgoRiesgoAdmin(admin.ModelAdmin):
    list_display = ('id', 'informe', 'sector_planta', 'estado', 'es_condicion_insegura')
    list_filter = ('estado', 'es_condicion_insegura')
    search_fields = ('sector_planta', 'descripcion_desvio')


# ==========================================
# MODELOS DE AUDITORÍA (NUEVOS)
# ==========================================

@admin.register(CategoriaPregunta)
class CategoriaPreguntaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'orden')
    list_editable = ('orden',)
    search_fields = ('nombre',)
    ordering = ('orden',)


@admin.register(PreguntaAuditoria)
class PreguntaAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'categoria', 'texto_corto', 'activo', 'orden')
    list_filter = ('categoria', 'activo')
    search_fields = ('texto',)
    ordering = ('categoria__orden', 'orden')

    def texto_corto(self, obj):
        return obj.texto[:60] + "..." if len(obj.texto) > 60 else obj.texto
    texto_corto.short_description = "Texto (resumen)"


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha_creacion', 'realizado_por')
    list_filter = ('fecha_creacion',)
    search_fields = ('cliente__nombre_fantasia',)


@admin.register(RespuestaAuditoria)
class RespuestaAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'auditoria', 'pregunta', 'valor')
    list_filter = ('valor', 'auditoria__cliente__organizacion')
    search_fields = ('auditoria__cliente__nombre_fantasia', 'pregunta__texto')