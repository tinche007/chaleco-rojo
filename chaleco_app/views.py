from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages  
from django.db.models import Prefetch
from django.db import transaction

from .models import ClienteEmpresa, InformeVisita, HallazgoRiesgo, Organizacion, PerfilUsuario
from .models import CategoriaPregunta, Auditoria, RespuestaAuditoria, PreguntaAuditoria, ClienteEmpresa

# IMPORTS PARA LA GENERACIÓN DEL PDF
import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

# IMPORTS PARA EL ASISTENTE DE IA
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import requests  
import traceback 

def inicio_view(request):
    """
    Vista principal que renderiza el menú en cuadrícula (mosaico)
    de Chaleco Rojo.
    """
    return render(request, 'inicio.html')


# @login_required
def crear_informe_view(request):
    # 1. Unificamos la obtención de la organización de manera segura
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
            actual_user = request.user
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
            actual_user = request.user
    else:
        mi_organizacion = Organizacion.objects.first() 
        actual_user = None

    if request.method == 'POST':
        # 🟢 CORRECCIÓN: Usamos .strip() y validamos que no sea un string vacío
        cliente_id = request.POST.get('cliente', '').strip()
        establecimiento_libre = request.POST.get('establecimiento_ocasional', '').strip()
        
        # NUEVOS: Capturamos los datos extras del cliente ocasional
        cuit_libre = request.POST.get('cuit_ocasional', '').strip()
        direccion_libre = request.POST.get('direccion_ocasional', '').strip()
        
        texto_resumen = request.POST.get('observaciones_generales')

    # Unificamos la obtención de la organización de manera segura
        nuevo_informe = InformeVisita(
            organizacion=mi_organizacion,
            inspector=actual_user,
            observaciones_generales=texto_resumen
        )

        # 🟢 CONTROL ESTRICTO DE VACÍOS: Evaluamos si realmente llegó un ID numérico válido
        if cliente_id and cliente_id != "":
            if mi_organizacion:
                nuevo_informe.cliente = ClienteEmpresa.objects.get(id=cliente_id, organizacion=mi_organizacion)
            else:
                nuevo_informe.cliente = ClienteEmpresa.objects.get(id=cliente_id)
        
        elif establecimiento_libre:
            # Ahora sí, al estar limpio el 'cliente_id', Django entra acá obligatoriamente
            nuevo_cliente, creado = ClienteEmpresa.objects.get_or_create(
                nombre_fantasia=establecimiento_libre,
                organizacion=mi_organizacion,
                defaults={
                    'razon_social': establecimiento_libre,
                    'cuit': cuit_libre,            # 🟢 SE AGREGA EL CUIT
                    'direccion': direccion_libre,  # 🟢 SE AGREGA LA DIRECCIÓN
                    'activo': True
                }
            )
            nuevo_informe.cliente = nuevo_cliente
            nuevo_informe.establecimiento_ocasional = establecimiento_libre
            
            if creado:
                messages.info(request, f"Se ha registrado automáticamente '{establecimiento_libre}' como nuevo cliente con sus datos completos.")
        else:
            # Si mandaron ambos vacíos
            pass
        
        # Guardamos el informe principal
        nuevo_informe.save()
        
        # 2. CAPTURAMOS LOS LISTADOS DINÁMICOS
        sectores = request.POST.getlist('sector[]')
        desvios = request.POST.getlist('desvio[]')
        medias = request.POST.getlist('medida[]')
        fotos = request.FILES.getlist('foto_evidencia[]')

        for i in range(len(sectores)):
            if sectores[i].strip() or desvios[i].strip():
                foto_fila = fotos[i] if i < len(fotos) else None

                HallazgoRiesgo.objects.create(
                    informe=nuevo_informe,
                    sector_planta=sectores[i],
                    descripcion_desvio=desvios[i],
                    medida_correctiva_sugerida=medias[i],
                    foto_evidencia=foto_fila,
                    estado='Abierto'
                )

        messages.success(request, "¡Informe y todos los hallazgos han sido guardados con éxito!")
        return redirect('crear_informe')

    else:
        # 🟢 EQUILIBRAMOS EL FILTRO PARA EL RENDER
        if mi_organizacion:
            mis_clientes = ClienteEmpresa.objects.filter(organizacion=mi_organizacion, activo=True)
        else:
            mis_clientes = ClienteEmpresa.objects.filter(activo=True)
        
        return render(request, 'crear_informe.html', {'clientes': mis_clientes})


def historial_informes_view(request):
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        informes = InformeVisita.objects.filter(organizacion=mi_organizacion).order_by('-fecha_visita')
    else:
        informes = InformeVisita.objects.all().order_by('-fecha_visita')

    return render(request, 'historial_informes.html', {'informes': informes})


def eliminar_informe_view(request, informe_id):
    """
    Elimina físicamente un informe de visita del historial.
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    # Buscamos de forma segura que el informe corresponda a la organización
    if mi_organizacion:
        informe = get_object_or_404(InformeVisita, id=informe_id, organizacion=mi_organizacion)
    else:
        informe = get_object_or_404(InformeVisita, id=informe_id)

    if request.method == 'POST':
        informe.delete()
        messages.success(request, "El informe de visita ha sido eliminado correctamente.")
        
    return redirect('historial_informes')


# VISTA PARA EXPORTAR EL REPORTE EN PDF
def exportar_pdf_view(request, informe_id):
    try:
        informe = InformeVisita.objects.get(id=informe_id)
    except InformeVisita.DoesNotExist:
        return HttpResponse("El informe solicitado no existe.", status=404)

    # Preparamos el contexto
    context = {
        'informe': informe,
    }
    
    # Renderizamos la plantilla
    template = get_template('exportar_pdf.html')
    html = template.render(context)

 # Función para resolver rutas de imágenes corregida y normalizada
    def link_callback(uri, rel):
        """
        Convierte URIs (ej. /media/fotos/... o URLs absolutas) 
        en rutas del sistema de archivos para xhtml2pdf.
        """
        # Si es una URL de media (subida por usuario)
        if uri.startswith('/media/'):
            # Eliminamos el prefijo y normalizamos la ruta del sistema operativo
            relative_path = uri.replace('/media/', '')
            path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, relative_path))
            
            # Verificación de control: Si el archivo físico no existe, xhtml2pdf fallará en silencio
            if os.path.exists(path):
                return path
            else:
                print(f"ALERTA: El archivo no existe en el disco: {path}")
                
        # Si es una URL estática (css, js)
        elif uri.startswith('/static/'):
            relative_path = uri.replace('/static/', '')
            path = os.path.normpath(os.path.join(settings.STATIC_ROOT, relative_path))
            if os.path.exists(path):
                return path

        elif uri.startswith(('http://', 'https://')):
            return uri

    # Configuramos la respuesta
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Legajo_Tecnico_{informe_id}.pdf"'

    # Generamos el PDF con el link_callback
    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        link_callback=link_callback,
        encoding='utf-8'
    )

    if pisa_status.err:
        print(f"Error en xhtml2pdf: {pisa_status.err}")  # Para depuración
        return HttpResponse('Ocurrió un error al generar el PDF.', status=500)

    return response


# ==========================================
# SECCIÓN PUNTO 3: GESTIÓN DE CLIENTES/EMPRESAS
# ==========================================

def lista_clientes_view(request):
    """
    Lista todos los clientes/empresas separados por Activos e Inactivos (Bajas).
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    # Traemos las empresas separadas por su estado (activo True o False)
    if mi_organizacion:
        empresas_activas = ClienteEmpresa.objects.filter(organizacion=mi_organizacion, activo=True)
        empresas_bajas = ClienteEmpresa.objects.filter(organizacion=mi_organizacion, activo=False)
    else:
        empresas_activas = ClienteEmpresa.objects.filter(activo=True)
        empresas_bajas = ClienteEmpresa.objects.filter(activo=False)

    context = {
        'empresas_activas': empresas_activas,
        'empresas_bajas': empresas_bajas,
    }
    return render(request, 'lista_clientes.html', context)


def alta_cliente_view(request):
    """
    Muestra el formulario y procesa el alta de un nuevo cliente/empresa.
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    if request.method == 'POST':
        razon_social = request.POST.get('razon_social')
        nombre_fantasia = request.POST.get('nombre_fantasia')
        cuit = request.POST.get('cuit')
        direccion = request.POST.get('direccion')
        telefono = request.POST.get('telefono')
        email = request.POST.get('email')

        # Validación: Evitamos duplicar CUITs dentro de la misma organización
        if mi_organizacion and ClienteEmpresa.objects.filter(cuit=cuit, organizacion=mi_organizacion).exists():
            messages.error(request, "Ya existe una empresa registrada con ese CUIT en tu organización.")
            return redirect('alta_cliente')

        # Creamos el nuevo cliente amarrado a la organización correspondiente
        ClienteEmpresa.objects.create(
            organizacion=mi_organizacion,
            razon_social=razon_social,
            nombre_fantasia=nombre_fantasia,
            cuit=cuit,
            direccion=direccion,
            telefono=telefono,
            email=email,
            activo=True # Nos aseguramos de que empiece activo
        )
        
        messages.success(request, f"¡Empresa '{nombre_fantasia}' dada de alta correctamente!")
        return redirect('lista_clientes')

    return render(request, 'alta_cliente.html')


def baja_cliente_view(request, cliente_id):
    """
    Realiza la baja lógica (ocultar de las listas) del cliente.
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    # Buscamos el cliente asegurándonos que sea de su organización
    if mi_organizacion:
        try:
            cliente = ClienteEmpresa.objects.get(id=cliente_id, organizacion=mi_organizacion)
        except ClienteEmpresa.DoesNotExist:
            return HttpResponse("No tenés permisos o la empresa no existe.", status=403)
    else:
        try:
            cliente = ClienteEmpresa.objects.get(id=cliente_id)
        except ClienteEmpresa.DoesNotExist:
            return HttpResponse("La empresa no existe.", status=404)

    if request.method == 'POST':
        cliente.activo = False  # Baja lógica: cambia el estado a Inactivo sin borrar el historial
        cliente.save()
        messages.success(request, f"La empresa '{cliente.nombre_fantasia}' fue dada de baja con éxito.")
        return redirect('lista_clientes')

    return render(request, 'confirmar_baja.html', {'cliente': cliente})


def reactivar_cliente_view(request, cliente_id):
    """
    Reactivar una empresa dada de baja.
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id)

    if request.method == 'POST':
        cliente.activo = True
        cliente.save()
        messages.success(request, f"La empresa '{cliente.nombre_fantasia}' ha sido reactivada correctamente.")
        return redirect('lista_clientes')

    return render(request, 'confirmar_reactivacion.html', {'cliente': cliente})


def detalle_cliente_view(request, cliente_id):
    """
    Muestra la ficha técnica detallada de una empresa específica
    junto con su historial de visitas asignadas.
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = None
    else:
        mi_organizacion = None

    # 1. Buscamos el cliente según la organización
    if mi_organizacion:
        empresa = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        empresa = get_object_or_404(ClienteEmpresa, id=cliente_id)
        
    # 2. TRAEMOS SOLAMENTE LAS VISITAS ASIGNADAS A ESTE CLIENTE
    # Usamos filter() en lugar de all() y ordenamos por fecha más reciente
    visitas_asignadas = InformeVisita.objects.filter(cliente=empresa).order_by('-fecha_visita')

    # 3. Pasamos tanto el cliente como sus visitas al contexto
    context = {
        'cliente': empresa,
        'visitas': visitas_asignadas
    }
    return render(request, 'detalle_cliente.html', context)


# ==========================================
# SECCIÓN: ASISTENTE DE INTELIGENCIA ARTIFICIAL
# ==========================================
@csrf_exempt
def asistente_ia_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mensaje_usuario = data.get('mensaje', '')
            api_key = "AQ.Ab8RN6KBqRmGlsjmHyDL9R4cAB3ooheUbxZ-ZZGOH-YG716hAA" 
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

            payload = {
                "system_instruction": {
                    "parts": [{
                        "text": (
                            "Eres el asistente inteligente de la aplicación 'Chaleco Rojo'. "
                            "Tu única función es ayudar a los usuarios a navegar y utilizar las funciones de esta aplicación. "
                            "Las funciones principales son: 1. Crear informes de visitas, 2. Ver historial, 3. Gestionar clientes, 4. Consultar estadísticas, 5. Acceder a checklists y leyes. "
                            "Si el usuario pregunta sobre los servicios de la empresa, historia o temas ajenos a la operativa de la aplicación, "
                            "debes responder amablemente que solo estás capacitado para ayudar con las gestiones de la aplicación y sugerirle "
                            "que visite el sitio web oficial 'www.chalecorojo.com' para obtener información sobre la empresa. "
                            "Responde siempre de forma profesional, concisa y enfocada en la app."
                        )
                    }]
                },
                "contents": [{"role": "user", "parts": [{"text": mensaje_usuario}]}]
            }

            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                res_json = response.json()
                if 'candidates' in res_json and len(res_json['candidates']) > 0:
                    texto = res_json['candidates'][0]['content']['parts'][0]['text']
                    return JsonResponse({'respuesta': texto})
                else:
                    return JsonResponse({'error': 'La IA bloqueó el contenido.'}, status=500)
            else:
                print(f"ERROR DE API: {response.text}")
                return JsonResponse({'error': 'Error de API. Revisá la terminal.'}, status=500)

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'error': 'Error interno'}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=400)


# ==========================================
# SECCIÓN: AUDITORÍAS
# ==========================================

def lista_auditorias(request):
    """
    Lista todas las auditorías realizadas por la organización.
    """
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except PerfilUsuario.DoesNotExist:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        auditorias = Auditoria.objects.filter(cliente__organizacion=mi_organizacion).select_related('cliente')
        clientes = ClienteEmpresa.objects.filter(organizacion=mi_organizacion, activo=True)
    else:
        auditorias = Auditoria.objects.all().select_related('cliente')
        clientes = ClienteEmpresa.objects.filter(activo=True)

    # Enriquecer cada auditoría con el conteo de respuestas
    for auditoria in auditorias:
        respuestas = auditoria.respuestas.all()
        auditoria.total_preguntas = respuestas.count()
        auditoria.total_no = respuestas.filter(valor='NO').count()
        auditoria.total_si = respuestas.filter(valor='SI').count()
        auditoria.total_na = respuestas.filter(valor='N/A').count()
        
        # Si la auditoría tiene respuestas pero sigue en progreso, recalcular
        if auditoria.total_preguntas > 0 and auditoria.resultado == 'en_progreso':
            if auditoria.total_no == 0:
                auditoria.resultado = 'apto'
            elif auditoria.total_no <= 5:
                auditoria.resultado = 'observaciones'
            else:
                auditoria.resultado = 'no_apto'
            auditoria.save()

    context = {
        'auditorias': auditorias,
        'clientes': clientes,
        'total_auditorias': auditorias.count(),
    }
    return render(request, 'lista_auditorias.html', context)


def realizar_auditoria(request, cliente_id):
    """
    Realiza una auditoría para un cliente específico. SIEMPRE empieza desde cero (N/A).
    """
    # 1. Obtener el cliente
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except PerfilUsuario.DoesNotExist:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id)

    # 🔥 SIEMPRE crear una auditoría NUEVA (no buscar una existente)
    # Eliminar auditoría anterior si existe (opcional)
    Auditoria.objects.filter(cliente=cliente, tipo='completa').delete()
    
    # Crear una nueva auditoría
    auditoria = Auditoria.objects.create(
        cliente=cliente,
        tipo='completa',
        realizado_por=request.user if request.user.is_authenticated else None,
        resultado='en_progreso'
    )

    # 2. Procesar POST (guardar respuestas)
    if request.method == 'POST':
        with transaction.atomic():
            no_count = 0
            total_preguntas = 0
            
            for key, value in request.POST.items():
                if key.startswith('preg_'):
                    pregunta_id = key.split('_')[1]
                    total_preguntas += 1
                    try:
                        pregunta = PreguntaAuditoria.objects.get(id=pregunta_id)
                        RespuestaAuditoria.objects.create(
                            auditoria=auditoria,
                            pregunta=pregunta,
                            valor=value
                        )
                        if value == 'NO':
                            no_count += 1
                    except PreguntaAuditoria.DoesNotExist:
                        pass

            # Calcular resultado
            if total_preguntas > 0:
                if no_count == 0:
                    auditoria.resultado = 'apto'
                elif no_count <= 5:
                    auditoria.resultado = 'observaciones'
                else:
                    auditoria.resultado = 'no_apto'
                auditoria.save()

        messages.success(request, f"Auditoría de {cliente.nombre_fantasia} guardada correctamente.")
        return redirect('resultado_auditoria', cliente_id=cliente.id)

    # 3. Obtener preguntas agrupadas por categoría para el GET
    categorias = []
    for cat in CategoriaPregunta.objects.all().order_by('orden'):
        preguntas = cat.preguntas.filter(activo=True).order_by('orden')
        if preguntas.exists():
            # 🔥 No cargar respuestas guardadas (siempre N/A)
            preguntas_con_respuesta = []
            for p in preguntas:
                preguntas_con_respuesta.append({
                    'id': p.id,
                    'texto': p.texto,
                    'respuesta_guardada': None  # 🔥 Siempre N/A
                })
            
            categorias.append({
                'nombre': cat.nombre,
                'preguntas_filtradas': preguntas_con_respuesta,
            })

    context = {
        'cliente': cliente,
        'auditoria': auditoria,
        'categorias': categorias,
        'tiene_preguntas': len(categorias) > 0,
        'OPCIONES': ['SI', 'NO', 'N/A'],
    }
    return render(request, 'auditorias.html', context)


def resultado_auditoria(request, cliente_id):
    """
    Muestra los resultados detallados de una auditoría.
    """
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except PerfilUsuario.DoesNotExist:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id)

    auditoria = get_object_or_404(Auditoria, cliente=cliente)
    respuestas = auditoria.respuestas.select_related('pregunta__categoria').all()

    # Estadísticas
    total_no = respuestas.filter(valor='NO').count()
    total_si = respuestas.filter(valor='SI').count()
    total_na = respuestas.filter(valor='N/A').count()
    total_respuestas = respuestas.count()

    # Calificación
    if total_respuestas == 0:
        calificacion = 'Sin datos'
        clase_calificacion = 'secondary'
        icono = 'fa-question-circle'
    elif total_no == 0:
        calificacion = 'Excelente'
        clase_calificacion = 'success'
        icono = 'fa-check-circle'
    elif total_no <= 5:
        calificacion = 'Bueno'
        clase_calificacion = 'info'
        icono = 'fa-thumbs-up'
    elif total_no <= 10:
        calificacion = 'Regular'
        clase_calificacion = 'warning'
        icono = 'fa-exclamation-triangle'
    else:
        calificacion = 'Condicional / Crítico'
        clase_calificacion = 'danger'
        icono = 'fa-times-circle'

    # Porcentaje de cumplimiento
    porcentaje = int((total_si / total_respuestas * 100)) if total_respuestas > 0 else 0

    # Agrupar NOs por categoría
    no_por_categoria = {}
    for r in respuestas.filter(valor='NO'):
        cat = r.pregunta.categoria.nombre
        no_por_categoria.setdefault(cat, []).append(r.pregunta.texto)

    context = {
        'cliente': cliente,
        'auditoria': auditoria,
        'total_no': total_no,
        'total_si': total_si,
        'total_na': total_na,
        'total_respuestas': total_respuestas,
        'calificacion': calificacion,
        'clase_calificacion': clase_calificacion,
        'icono_calificacion': icono,
        'porcentaje': porcentaje,
        'no_por_categoria': no_por_categoria,
    }
    return render(request, 'auditoria_resultado.html', context)


def test_view(request):
    """Vista de prueba para verificar la herencia de templates"""
    return render(request, 'test.html')


# ==========================================
# AUDITORÍA EXPRESS - GUARDA EN BASE DE DATOS
# ==========================================

def auditoria_express(request, cliente_id):
    """Auditoría Express de 10 preguntas - SIEMPRE empieza desde cero"""
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except (AttributeError, PerfilUsuario.DoesNotExist):
        mi_organizacion = Organizacion.objects.first()
    
    if mi_organizacion:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id)
    
    preguntas = [
        '¿Los extintores están vigentes, señalizados y accesibles?',
        '¿Las salidas de emergencia están despejadas y señalizadas?',
        '¿Los operarios usan EPP correctamente (cascos, calzado, etc.)?',
        '¿Los arneses y líneas de vida están en buen estado y con inspección diaria?',
        '¿Las máquinas tienen protecciones (resguardos) en partes móviles?',
        '¿Los tableros eléctricos tienen tapas y están correctamente señalizados?',
        '¿Los pasillos y áreas de trabajo están ordenados y limpios?',
        '¿Se cuenta con permisos para trabajos en altura o en caliente?',
        '¿Los operarios tienen capacitación y carnets vigentes (autoelevador, altura)?',
        '¿Los residuos peligrosos están correctamente almacenados y señalizados?',
    ]
    
    # 🔥 ELIMINAR auditoría anterior si existe
    Auditoria.objects.filter(cliente=cliente, tipo='express').delete()
    
    # Crear una nueva auditoría Express
    auditoria = Auditoria.objects.create(
        cliente=cliente,
        tipo='express',
        realizado_por=request.user if request.user.is_authenticated else None,
        observaciones=request.POST.get('observaciones', '')
    )
    
    if request.method == 'POST':
        # Guardar respuestas
        no_count = 0
        for i, pregunta_texto in enumerate(preguntas):
            valor = request.POST.get(f'preg_{i}', 'N/A')
            RespuestaAuditoria.objects.create(
                auditoria=auditoria,
                pregunta_texto=pregunta_texto,
                valor=valor
            )
            if valor == 'NO':
                no_count += 1
        
        # Calcular resultado
        if no_count == 0:
            auditoria.resultado = 'apto'
        elif no_count <= 3:
            auditoria.resultado = 'observaciones'
        else:
            auditoria.resultado = 'no_apto'
        auditoria.save()
        
        messages.success(request, f"✅ Auditoría Express completada para {cliente.nombre_fantasia}")
        return redirect('lista_auditorias')
    
    context = {
        'cliente': cliente,
        'preguntas': preguntas,
        'respuestas': ['N/A'] * len(preguntas),  # 🔥 Siempre N/A
        'observaciones_guardadas': '',
    }
    return render(request, 'auditoria_express.html', context)

def resultado_auditoria_express(request, cliente_id):
    """Muestra los resultados detallados de una auditoría Express"""
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except (AttributeError, PerfilUsuario.DoesNotExist):
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id)

    # Buscar la última auditoría Express para este cliente
    auditoria = Auditoria.objects.filter(
        cliente=cliente,
        tipo='express'
    ).order_by('-fecha_creacion').first()

    if not auditoria:
        messages.warning(request, "No hay auditoría Express para este cliente.")
        return redirect('lista_auditorias')

    respuestas = auditoria.respuestas.all()
    total_preguntas = respuestas.count()
    total_no = respuestas.filter(valor='NO').count()
    total_si = respuestas.filter(valor='SI').count()
    total_na = respuestas.filter(valor='N/A').count()

    # Calcular resultado
    if total_no == 0:
        resultado_texto = '🟢 APTO'
        clase_resultado = 'apto'
    elif total_no <= 3:
        resultado_texto = '🟡 CON OBSERVACIONES'
        clase_resultado = 'observaciones'
    else:
        resultado_texto = '🔴 NO APTO'
        clase_resultado = 'no_apto'

    # Agrupar respuestas por tipo para mostrar
    respuestas_si = respuestas.filter(valor='SI')
    respuestas_no = respuestas.filter(valor='NO')
    respuestas_na = respuestas.filter(valor='N/A')

    context = {
        'cliente': cliente,
        'auditoria': auditoria,
        'respuestas': respuestas,
        'respuestas_si': respuestas_si,
        'respuestas_no': respuestas_no,
        'respuestas_na': respuestas_na,
        'total_preguntas': total_preguntas,
        'total_no': total_no,
        'total_si': total_si,
        'total_na': total_na,
        'resultado_texto': resultado_texto,
        'clase_resultado': clase_resultado,
    }
    return render(request, 'auditoria_resultado_express.html', context)

    # ==========================================
# DASHBOARD DE ESTADÍSTICAS
# ==========================================

def dashboard_view(request):
    """
    Panel de control con estadísticas de Chaleco Rojo
    """
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except (AttributeError, PerfilUsuario.DoesNotExist):
        mi_organizacion = Organizacion.objects.first()

    # --- 1. KPIs Básicos ---
    total_auditorias = Auditoria.objects.filter(cliente__organizacion=mi_organizacion).count()
    total_informes = InformeVisita.objects.filter(organizacion=mi_organizacion).count()
    total_clientes = ClienteEmpresa.objects.filter(organizacion=mi_organizacion, activo=True).count()
    total_hallazgos = HallazgoRiesgo.objects.filter(informe__organizacion=mi_organizacion).count()
    hallazgos_abiertos = HallazgoRiesgo.objects.filter(informe__organizacion=mi_organizacion, estado='Abierto').count()
    hallazgos_cerrados = HallazgoRiesgo.objects.filter(informe__organizacion=mi_organizacion, estado='Cerrado').count()

    # --- 2. Auditorías por mes (últimos 6 meses) ---
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    import datetime

    hoy = datetime.date.today()
    seis_meses_atras = hoy - datetime.timedelta(days=180)

    auditorias_por_mes = (
        Auditoria.objects
        .filter(cliente__organizacion=mi_organizacion, fecha_creacion__date__gte=seis_meses_atras)
        .annotate(mes=TruncMonth('fecha_creacion'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    meses = []
    cantidades = []
    for item in auditorias_por_mes:
        meses.append(item['mes'].strftime('%b') if item['mes'] else '')
        cantidades.append(item['total'])

    # --- 3. Auditorías por tipo ---
    express_count = Auditoria.objects.filter(cliente__organizacion=mi_organizacion, tipo='express').count()
    completa_count = Auditoria.objects.filter(cliente__organizacion=mi_organizacion, tipo='completa').count()

    # --- 4. Resultados de auditorías ---
    apto_count = Auditoria.objects.filter(cliente__organizacion=mi_organizacion, resultado='apto').count()
    obs_count = Auditoria.objects.filter(cliente__organizacion=mi_organizacion, resultado='observaciones').count()
    no_apto_count = Auditoria.objects.filter(cliente__organizacion=mi_organizacion, resultado='no_apto').count()
    en_progreso_count = Auditoria.objects.filter(cliente__organizacion=mi_organizacion, resultado='en_progreso').count()

    # --- 5. Top 5 clientes con más auditorías ---
    top_clientes = (
        Auditoria.objects
        .filter(cliente__organizacion=mi_organizacion)
        .values('cliente__nombre_fantasia', 'cliente__id')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    # --- 6. Hallazgos por estado ---
    hallazgos_por_estado = (
        HallazgoRiesgo.objects
        .filter(informe__organizacion=mi_organizacion)
        .values('estado')
        .annotate(total=Count('id'))
    )

    # --- 7. Hallazgos por sector (top 5) ---
    hallazgos_por_sector = (
        HallazgoRiesgo.objects
        .filter(informe__organizacion=mi_organizacion)
        .values('sector_planta')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    # 🔥 AGREGAR: Últimos hallazgos para mostrar en el dashboard
    ultimos_hallazgos = (
        HallazgoRiesgo.objects
        .filter(informe__organizacion=mi_organizacion)
        .select_related('informe')
        .order_by('-informe__fecha_visita')[:5]
    )

    context = {
        # KPIs
        'total_auditorias': total_auditorias,
        'total_informes': total_informes,
        'total_clientes': total_clientes,
        'total_hallazgos': total_hallazgos,
        'hallazgos_abiertos': hallazgos_abiertos,
        'hallazgos_cerrados': hallazgos_cerrados,
        
        # Auditorías por mes
        'meses': meses,
        'cantidades': cantidades,
        
        # Auditorías por tipo
        'express_count': express_count,
        'completa_count': completa_count,
        
        # Resultados
        'apto_count': apto_count,
        'obs_count': obs_count,
        'no_apto_count': no_apto_count,
        'en_progreso_count': en_progreso_count,
        
        # Top clientes
        'top_clientes': top_clientes,
        
        # Hallazgos por estado
        'hallazgos_por_estado': hallazgos_por_estado,
        
        # Hallazgos por sector
        'hallazgos_por_sector': hallazgos_por_sector,
        
        # 🔥 NUEVO: Últimos hallazgos
        'ultimos_hallazgos': ultimos_hallazgos,
    }
    
    return render(request, 'dashboard.html', context)


def historial_informes_view(request):
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        informes = InformeVisita.objects.filter(organizacion=mi_organizacion).order_by('-fecha_visita')
    else:
        informes = InformeVisita.objects.all().order_by('-fecha_visita')

    # 🔥 FILTRO POR SECTOR (desde el Dashboard)
    sector_filtro = request.GET.get('sector')
    if sector_filtro:
        informes = informes.filter(hallazgos__sector_planta__iexact=sector_filtro).distinct()
        messages.info(request, f"📌 Mostrando informes con hallazgos en: {sector_filtro}")

    return render(request, 'historial_informes.html', {'informes': informes})


def eliminar_cliente_view(request, cliente_id):
    """
    Elimina físicamente un cliente de la base de datos.
    """
    if request.user.is_authenticated:
        try:
            mi_organizacion = request.user.perfilusuario.organizacion
        except PerfilUsuario.DoesNotExist:
            mi_organizacion = Organizacion.objects.first()
    else:
        mi_organizacion = Organizacion.objects.first()

    if mi_organizacion:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id, organizacion=mi_organizacion)
    else:
        cliente = get_object_or_404(ClienteEmpresa, id=cliente_id)

    if request.method == 'POST':
        nombre = cliente.nombre_fantasia
        cliente.delete()
        messages.success(request, f"✅ Cliente '{nombre}' eliminado permanentemente.")
        return redirect('lista_clientes')

    return render(request, 'confirmar_eliminar_cliente.html', {'cliente': cliente})

def documentacion_view(request):
    """Módulo de gestión documental - Lee archivos automáticamente con tamaño"""
    try:
        mi_organizacion = request.user.perfilusuario.organizacion
    except (AttributeError, PerfilUsuario.DoesNotExist):
        mi_organizacion = Organizacion.objects.first()
    
    documentos_path = os.path.join(settings.MEDIA_ROOT, 'documentos')
    categorias = {}
    
    if os.path.exists(documentos_path):
        for carpeta in os.listdir(documentos_path):
            carpeta_path = os.path.join(documentos_path, carpeta)
            if os.path.isdir(carpeta_path):
                archivos = []
                for archivo in os.listdir(carpeta_path):
                    archivo_path = os.path.join(carpeta_path, archivo)
                    if os.path.isfile(archivo_path):
                        extension = os.path.splitext(archivo)[1][1:].lower()
                        if not extension:
                            extension = 'txt'
                        
                        # Obtener tamaño del archivo
                        size_bytes = os.path.getsize(archivo_path)
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes / 1024:.1f} KB"
                        else:
                            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                        
                        archivos.append({
                            'nombre': archivo,
                            'extension': extension,
                            'url': f'/media/documentos/{carpeta}/{archivo}',
                            'tamaño': size_str,
                        })
                if archivos:
                    categorias[carpeta] = archivos
    
    iconos = {
        'ATS': '📋',
        'Capacitaciones': '🧢',
        'EPP': '🪖',
        'matriz de riesgo': '📊',
        'PTS': '📋',
        'planes': '📋',
        'checklist': '✅',
        'carga de fuego': '🔥',
        'documentaciones': '📁',
        'evaluación de cursos': '📝',
        'informes ambientales': '🌿',
        'presupuestos': '💰',
        'protocolos': '📜',
        'PS': '📋',
        'RGRL': '📋',
        'accidentabilidad': '📊',
    }
    
    context = {
        'organizacion': mi_organizacion,
        'categorias': dict(sorted(categorias.items(), key=lambda x: x[0].lower())),
        'iconos': iconos,
    }
    return render(request, 'documentacion.html', context)