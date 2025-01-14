
# Bot de Notificación de Hitos y Facturación

Este proyecto es un bot desarrollado en Python que integra información de proyectos desde un sistema Odoo utilizando `xmlrpc`, procesa la información con `pandas`, y la publica en un canal de Discord mediante webhooks. El bot está diseñado para notificar acerca de:

- **Hitos Vencidos.**
- **Fechas de vencimiento de hitos.**
- **Porcentaje restante de facturación por proyecto.**

El bot se puede configurar para ejecutarse automáticamente mediante `cron`, ajustando la periodicidad según sea necesario.

---

## Características

1. **Integración con Odoo:** Se conecta a la base de datos de Odoo usando la biblioteca `xmlrpc` para obtener la información de los hitos y la facturación.
2. **Procesamiento de datos:** Utiliza `pandas` para manipular y analizar los datos obtenidos.
3. **Notificaciones a Discord:** Envía mensajes personalizados a un canal de Discord mediante un webhook.
4. **Automatización:** Diseñado para ejecutarse en horarios predefinidos utilizando `cron`.

---

## Requisitos

- **Python 3.5+**
- Dependencias:
  - `xmlrpc.client`
  - `pandas`
  - `requests`
- Acceso a:
  - Una base de datos de Odoo.
  - Un canal de Discord con webhook configurado.
  - Un sistema con soporte para `cron` (Linux/macOS).

---

## Instalación

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/crisdavico/eynes_discord_bot.git
   cd eynes_discord_bot
   ```

2. **Instalar dependencias:**

   Utiliza `pip` para instalar las librerías necesarias:

   ```bash
   pip install -r requirements.txt
   ```

3. **Crear el archivo `.env`:**

   El archivo `.env` debe contener las credenciales de conexión y configuraciones del bot. Crea un archivo `.env` en el directorio del proyecto basado en el siguiente ejemplo:

   ```env
   # Configuración de Odoo
   ODOO_URL=http://tu-odoo.com       # URL del servidor Odoo
   ODOO_DB=nombre_de_base_de_datos   # Nombre de la base de datos de Odoo
   ODOO_USER=usuario                 # Usuario de Odoo
   ODOO_PASSWORD=contraseña          # Contraseña de Odoo

   # Configuración de Discord
   FILE_ID_WEBHOOKS=[str] # ID del archivo sheet para leer desde google drive
   DISCORD_ROLES={'ROLE_1': 'ID_ROLE'}
   ```

   Reemplaza los valores con la información correspondiente a tu instalación de Odoo y Discord.

4. **Probar la ejecución del bot:**

   Ejecuta el script manualmente para probar su funcionamiento:

   ```bash
   python bot.py
   ```

5. **Configurar `cron`:**

   ### Crear un Cron Job en Ubuntu

   En Ubuntu, sigue estos pasos para configurar el cron job:

   1. Abre el crontab para tu usuario:

      ```bash
      crontab -e
      ```

   2. Agrega una línea para ejecutar el bot automáticamente (por ejemplo, todos los días a las 9 AM):

      ```bash
      0 9 * * * /usr/bin/python3 /ruta/al/proyecto/bot.py
      ```

   3. Guarda y cierra el archivo. El cron job se activará automáticamente.

   ### Verificar Cron Jobs Activos

   Puedes listar tus cron jobs con el siguiente comando:

   ```bash
   crontab -l
   ```

---

## Uso

**Notificaciones:** El bot enviará mensajes en formato claro al canal de Discord especificado. Por ejemplo:

   ```
	Hola amigos de PROJECT_NAME! ¡Espero que estén muy bien! 
	Queríamos recordarles que: 
	Algunas fechas de cumplimiento de próximos hitos se están acercando. Agradecemos que realicen las revisiones necesarias para saber si estamos en camino o es necesario revisar fechas. 
	 
	Los hitos próximos a cumplirse son: 
	 
	[M00361] MÓDULO DE INVENTARIO Y DEPÓSITOS, vence en 7 días y queda facturar un 80.0%
	[M00362] MODULO PUNTO DE VENTA, vence en 56 días y queda facturar un 80.0%
	[M00357] MODULO ADMINISTRACIÓN, vence en 84 días y queda facturar un 80.0% 

	Si encuentran algún obstáculo o necesitan asistencia adicional, por favor no duden en contactarnos para asegurar un avance fluido. 
	Gracias por el compromiso y atención de siempre. 
	Dpto. Gestión
   ```
