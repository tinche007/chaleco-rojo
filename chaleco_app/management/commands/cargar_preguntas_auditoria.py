from django.core.management.base import BaseCommand
from chaleco_app.models import CategoriaPregunta, PreguntaAuditoria  # 🔥 CAMBIADO AQUÍ

class Command(BaseCommand):
    help = 'Carga las preguntas de auditoría desde un diccionario predefinido'

    def handle(self, *args, **options):
        # Definimos las categorías y preguntas basadas en la auditoría que desarrollamos
        categorias = [
            {
                'nombre': 'Gestión y Documentación',
                'orden': 1,
                'preguntas': [
                    '¿La empresa tiene designado un Servicio de Higiene y Seguridad (interno o externo) y está registrado ante la SRT?',
                    '¿Se ha elaborado el Programa Anual de Prevención (PAP) para el año en curso, firmado por el responsable y el servicio de higiene?',
                    '¿Existe un legajo técnico con las mediciones ambientales (ruido, iluminación, contaminantes, temperatura) de los últimos 2 años?',
                    '¿Se tienen las Fichas de Datos de Seguridad (HDS) de todos los productos químicos utilizados, actualizadas según SGA?',
                    '¿Se lleva un registro de capacitaciones en higiene y seguridad (con temario, fecha, asistencia y evaluación)?',
                    '¿Se han denunciado todos los accidentes/incidentes de trabajo a la ART en tiempo y forma (dentro de las 48 hs)?',
                    '¿La empresa cuenta con cobertura de ART vigente y está al día con el pago de sus obligaciones?',
                ]
            },
            {
                'nombre': 'Instalaciones, Orden y Limpieza',
                'orden': 2,
                'preguntas': [
                    '¿Los pisos están en buen estado, sin desniveles, grietas o superficies resbaladizas?',
                    '¿Los pasillos, rutas de evacuación y salidas de emergencia están despejados y claramente señalizados?',
                    '¿Los sanitarios, vestuarios y comedores están limpios, en buen estado y con provisión de agua caliente?',
                    '¿Hay agua potable disponible y accesible para el consumo del personal en todas las áreas?',
                    '¿Existe un programa de orden y limpieza (5S o similar) y se aplica efectivamente?',
                ]
            },
            {
                'nombre': 'Protección Contra Incendios',
                'orden': 3,
                'preguntas': [
                    '¿Hay matafuegos (extintores) en cantidad y tipo adecuado (ej. 1 cada 200 m², ABC para riesgos eléctricos/sólidos/líquidos)?',
                    '¿Los matafuegos están vigentes (con su última recarga y control anual) y accesibles (sin obstáculos)?',
                    '¿Las luces de emergencia funcionan y las señales de salida son visibles desde cualquier punto?',
                    '¿Se ha realizado algún simulacro de evacuación en el último año y se registró?',
                    '¿Los materiales inflamables se almacenan en un lugar seguro, ventilado y con señalización?',
                    '¿Existe un plan de emergencia escrito y conocido por el personal?',
                ]
            },
            {
                'nombre': 'Equipos de Protección Personal (EPP)',
                'orden': 4,
                'preguntas': [
                    '¿El empleador provee los EPP (cascos, lentes, guantes, protección auditiva, calzado de seguridad, arneses) sin costo para el trabajador?',
                    '¿Los EPP entregados cuentan con la certificación correspondiente (ej. norma IRAM, CE, ANSI)?',
                    '¿Existe un registro formal de entrega de EPP (con fecha, tipo de equipo, número de serie y firma del trabajador)?',
                    '¿Los trabajadores usan efectivamente los EPP en sus tareas diarias? (Verificación en el momento)',
                    '¿Se capacita a los trabajadores sobre el uso correcto, limpieza, mantenimiento y vida útil de los EPP?',
                    '¿Se realiza inspección periódica de los EPP (especialmente arneses, cascos, guantes dieléctricos) y se retiran los dañados?',
                ]
            },
            {
                'nombre': 'Trabajos en Altura',
                'orden': 5,
                'preguntas': [
                    '¿Se ha elaborado un procedimiento escrito para trabajos en altura y se aplica?',
                    '¿Los arneses de seguridad están en buen estado (sin costuras rotas, hebillas dañadas) y se inspeccionan diariamente?',
                    '¿Existen puntos de anclaje adecuados y resistentes (certificados) para cada trabajo en altura?',
                    '¿Los operarios que realizan trabajos en altura están capacitados y autorizados específicamente para ello?',
                    '¿Se utiliza línea de vida o sistema de detención de caídas en todos los trabajos en altura?',
                ]
            },
            {
                'nombre': 'Riesgo Eléctrico',
                'orden': 6,
                'preguntas': [
                    '¿Todos los tableros eléctricos tienen sus tapas y están debidamente señalizados?',
                    '¿Los cableados están contenidos en caños/canales y sin empalmes improvisados?',
                    '¿Existe un programa de mantenimiento de instalaciones eléctricas (termografías, mediciones de puesta a tierra)?',
                ]
            },
            {
                'nombre': 'Riesgos Mecánicos / Máquinas',
                'orden': 7,
                'preguntas': [
                    '¿Todas las máquinas tienen resguardos fijos o con enclavamiento que impiden el contacto con partes móviles?',
                    '¿Las máquinas tienen parada de emergencia (botón tipo hongo) accesible y operativa?',
                    '¿Se realizan inspecciones periódicas de seguridad a las máquinas y herramientas?',
                ]
            },
            {
                'nombre': 'Exposición a Ruido',
                'orden': 8,
                'preguntas': [
                    '¿Se han medido los niveles de ruido en los puestos de trabajo en el último año?',
                    '¿Se entrega protección auditiva (orejeras o tapones) a los operarios expuestos a más de 85 dB?',
                    '¿Se realizan audiometrías a los operarios expuestos a ruido (ingreso y periódicas)?',
                ]
            },
            {
                'nombre': 'Manipulación Manual de Cargas',
                'orden': 9,
                'preguntas': [
                    '¿Se han evaluado los riesgos ergonómicos por manipulación manual de cargas?',
                    '¿Se utilizan ayudas mecánicas (carros, polipastos, transpaletas) para cargas pesadas?',
                    '¿El personal está capacitado en técnicas seguras de levantamiento de cargas?',
                ]
            },
            {
                'nombre': 'Trabajos en Caliente (soldadura, corte)',
                'orden': 10,
                'preguntas': [
                    '¿Existe un permiso de trabajo en caliente para cada tarea de soldadura/corte?',
                    '¿Se cuenta con manta ignífuga o protección para evitar chispas en zonas con material combustible?',
                    '¿Hay un matafuego cerca del área de soldadura durante la ejecución de la tarea?',
                ]
            },
            {
                'nombre': 'Gestión Ambiental y Residuos',
                'orden': 11,
                'preguntas': [
                    '¿Se gestionan adecuadamente los residuos peligrosos (aceites usados, solventes, trapos contaminados, baterías)?',
                    '¿Se cuenta con el Manifiesto de Residuos Peligrosos y las autorizaciones ambientales correspondientes?',
                    '¿Existen diques de contención en áreas de almacenamiento de líquidos (tambores, tanques) para evitar derrames?',
                    '¿Los productos químicos están correctamente etiquetados y almacenados según compatibilidad?',
                    '¿Se registran las mediciones de contaminantes (gases, vapores, material particulado) en los puestos de trabajo?',
                ]
            },
            {
                'nombre': 'Autoelevadores / Montacargas',
                'orden': 12,
                'preguntas': [
                    '¿Los autoelevadores cuentan con cinturón de seguridad, luces de giro, balizas y alarma de retroceso?',
                    '¿Se realizan controles periódicos y se lleva un registro de mantenimiento de los autoelevadores?',
                    '¿Los operadores de autoelevadores están capacitados y autorizados (con carnet habilitante)?',
                    '¿El equipo tiene placa identificatoria visible con capacidad de carga, año y datos del fabricante?',
                ]
            },
            {
                'nombre': 'Salud Ocupacional y Capacitación',
                'orden': 13,
                'preguntas': [
                    '¿Se realizan exámenes médicos preocupacionales, periódicos y de egreso a todos los trabajadores?',
                    '¿Se cuenta con un botiquín de primeros auxilios completo y accesible en todas las áreas?',
                    '¿Existen personas capacitadas en primeros auxilios (RCP, manejo de emergencias) en cada turno?',
                    '¿El personal posee conocimientos apropiados sobre los riesgos específicos de su puesto de trabajo?',
                    '¿Se aplican pausas activas o programas de prevención de riesgos ergonómicos?',
                ]
            },
            {
                'nombre': 'Riesgo Psicosocial (Valor Agregado)',
                'orden': 14,
                'preguntas': [
                    '¿Se han evaluado los factores de riesgo psicosocial (carga mental, estrés, turnos, presión de tiempos)?',
                    '¿Existen pausas programadas en tareas de alta concentración o repetitivas?',
                    '¿Se promueve un clima laboral adecuado y canales de comunicación para reportar problemas?',
                ]
            },
        ]

        for cat_data in categorias:
            categoria, created = CategoriaPregunta.objects.get_or_create(
                nombre=cat_data['nombre'],
                defaults={'orden': cat_data['orden']}
            )
            if not created:
                # Si ya existe, actualizamos el orden por si cambió
                categoria.orden = cat_data['orden']
                categoria.save()

            for idx, pregunta_texto in enumerate(cat_data['preguntas']):
                PreguntaAuditoria.objects.get_or_create(
                    categoria=categoria,
                    texto=pregunta_texto,
                    defaults={'orden': idx}
                )

        self.stdout.write(self.style.SUCCESS('✅ Preguntas cargadas exitosamente'))
        self.stdout.write(f'📊 Total de categorías: {CategoriaPregunta.objects.count()}')
        self.stdout.write(f'📝 Total de preguntas: {PreguntaAuditoria.objects.count()}')