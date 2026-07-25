from django.db import models
from django.contrib.auth.models import User

# 1. EL ESPACIO DE TRABAJO (La Consultora)
class Organizacion(models.Model):
    nombre = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='logos_consultoras/', null=True, blank=True)
    color_primario = models.CharField(max_length=7, default='#1A446C')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# 2. EL PERFIL DEL INSPECTOR / USUARIO
class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE)
    es_administrador = models.BooleanField(default=False)


# 3. LOS CLIENTES DE LA CONSULTORA
class ClienteEmpresa(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE)
    nombre_fantasia = models.CharField(max_length=150)
    razon_social = models.CharField(max_length=150, null=True, blank=True)
    cuit = models.CharField(max_length=11, null=True, blank=True)
    direccion = models.CharField(max_length=200)
    provincia = models.CharField(max_length=100, default='Córdoba')
    telefono = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_fantasia


# 4. EL INFORME DE VISITA / AUDITORÍA
class InformeVisita(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE)
    cliente = models.ForeignKey(ClienteEmpresa, on_delete=models.SET_NULL, null=True, blank=True)
    establecimiento_ocasional = models.CharField(max_length=150, null=True, blank=True)
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_visita = models.DateTimeField(auto_now_add=True)
    observaciones_generales = models.TextField()

    def __str__(self):
        cliente_nombre = self.cliente.nombre_fantasia if self.cliente else self.establecimiento_ocasional
        return f"Informe {self.id} - {cliente_nombre} ({self.fecha_visita.strftime('%d/%m/%Y')})"


# 5. HALLAZGOS / DESVÍOS
class HallazgoRiesgo(models.Model):
    ESTADOS_CHOICES = [
        ('Abierto', 'Abierto'),
        ('En Progreso', 'En Progreso'),
        ('Cerrado', 'Cerrado'),
    ]
    
    informe = models.ForeignKey(InformeVisita, on_delete=models.CASCADE, related_name='hallazgos')
    sector_planta = models.CharField(max_length=100)
    descripcion_desvio = models.TextField()
    es_condicion_insegura = models.BooleanField(default=True)
    foto_evidencia = models.ImageField(upload_to='hallazgos_fotos/', null=True, blank=True)
    medida_correctiva_sugerida = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='Abierto')
    fecha_compromiso = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.sector_planta} - {self.descripcion_desvio[:30]}... ({self.estado})"


# 6. AUDITORÍAS - CATEGORÍAS Y PREGUNTAS
class CategoriaPregunta(models.Model):
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.nombre


class PreguntaAuditoria(models.Model):
    categoria = models.ForeignKey(CategoriaPregunta, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.TextField()
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"[{self.categoria.nombre}] {self.texto[:50]}..."


# 7. AUDITORÍA - MODELO PRINCIPAL
class Auditoria(models.Model):
    TIPO_CHOICES = [
        ('express', 'Express (10 preguntas)'),
        ('completa', 'Completa (61 preguntas)'),
    ]
    RESULTADO_CHOICES = [
        ('apto', 'Apto'),
        ('observaciones', 'Con Observaciones'),
        ('no_apto', 'No Apto'),
        ('en_progreso', 'En Progreso'),
    ]
    
    cliente = models.ForeignKey(ClienteEmpresa, on_delete=models.CASCADE, related_name='auditorias')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='completa')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    realizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default='en_progreso')
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.cliente.nombre_fantasia} - {self.get_tipo_display()} ({self.fecha_creacion.strftime('%d/%m/%Y')})"
    
    def get_resultado_display(self):
        if self.resultado == 'apto':
            return '🟢 APTO'
        elif self.resultado == 'observaciones':
            return '🟡 CON OBSERVACIONES'
        elif self.resultado == 'no_apto':
            return '🔴 NO APTO'
        else:
            return '⏳ En progreso'
    
    # 🔥 AGREGÁ ESTE MÉTODO
    def get_tipo_display(self):
        """Devuelve el tipo de auditoría con emoji"""
        if self.tipo == 'express':
            return '⚡ Express (10 preguntas)'
        else:
            return '📋 Completa (61 preguntas)'


# 8. RESPUESTAS DE AUDITORÍA
class RespuestaAuditoria(models.Model):
    OPCIONES = [
        ('SI', 'SÍ'),
        ('NO', 'NO'),
        ('N/A', 'N/A'),
    ]
    
    auditoria = models.ForeignKey(Auditoria, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(PreguntaAuditoria, on_delete=models.CASCADE, null=True, blank=True)
    pregunta_texto = models.CharField(max_length=500, null=True, blank=True)
    valor = models.CharField(max_length=3, choices=OPCIONES, default='N/A')

    class Meta:
        unique_together = ('auditoria', 'pregunta')

    def __str__(self):
        if self.pregunta:
            return f"{self.pregunta.id} - {self.valor}"
        return f"{self.pregunta_texto[:30] if self.pregunta_texto else 'Sin texto'}... - {self.valor}"