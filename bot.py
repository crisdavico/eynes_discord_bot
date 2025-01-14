import pandas as pd
import numpy as np
from datetime import datetime
import requests
import xmlrpc.client
from dotenv import load_dotenv
import os
import json
from io import StringIO



pd.set_option('display.max_columns', None)
pd.options.display.float_format = '{:,.2f}'.format
# Carga las variables del archivo .env
load_dotenv()


def connect_odoo():
    # Parámetros de conexión
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")

    # Autenticación
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})

    # Objeto models
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

    return (models, db, uid, password)

def get_milestone_df(models, db, uid, password):
    # Obtener datos de los hitos
    milestone_records = models.execute_kw(db, uid, password,
        'project.task', 'search_read',
        [[('task_type', '=', 'milestone'), '|', ('active', '=', True), ('active', '=', False)]], # Aquí puedes agregar filtros si es necesario
        {'fields': ['display_name', 'project_id', 'date_from', 'date_to', 'sale_line_id'],
        'context': {'lang': 'es_AR'}})

    milestone_df = pd.DataFrame(milestone_records)
    milestone_df.rename(columns={'display_name':'name'}, inplace=True)
    milestone_df['date_from'] = milestone_df['date_from'].replace({False: '1900-01-01 00:00:00'})
    milestone_df['date_to'] = milestone_df['date_to'].replace({False: '1900-01-01 00:00:00'})
    milestone_df['date_from'] = pd.to_datetime(milestone_df['date_from']).dt.date
    milestone_df['date_to'] = pd.to_datetime(milestone_df['date_to']).dt.date


    milestone_df[['project_db_id', 'project_name']] = pd.DataFrame(milestone_df['project_id'].tolist(), index=milestone_df.index)

    milestone_df['sale_line_id'] = milestone_df['sale_line_id'].apply(lambda x: x if isinstance(x, list) else [None, None])
    milestone_df[['sale_line_db_id', 'sale_line_name']] = pd.DataFrame(milestone_df['sale_line_id'].tolist(), index=milestone_df.index)

    # Obtener datos de las lineas de orden de venta
    sale_line_records = models.execute_kw(db, uid, password,
        'sale.order.line', 'search_read',
        [], # Aquí puedes agregar filtros si es necesario
        {'fields': ['name', 'create_date','price_subtotal', 'currency_id']})

    sale_line_df = pd.DataFrame(sale_line_records)
    sale_line_df[['currency_db_id', 'currency_name']] = pd.DataFrame(sale_line_df['currency_id'].tolist(), index=sale_line_df.index)


    #Unificar ambos df
    milestone_df = (milestone_df
                    .set_index('sale_line_db_id')
                    .join(sale_line_df
                        .drop(columns=['name','currency_id','currency_db_id'])
                        .set_index('id')
                        )
                    .drop(columns=['project_id','sale_line_id'])
                    ).reset_index()

    # Reformatear las fechas a 'MM-YYYY'
    milestone_df['create_date'] = pd.to_datetime(milestone_df['create_date'])
    milestone_df['sale_month'] = milestone_df['create_date'].dt.strftime('%m-%Y')

    milestone_df.rename(columns={
    'currency_name': 'sale_currency_name',
    'price_subtotal': 'sale_price_subtotal'
    }, inplace=True)

    invoices = models.execute_kw(db, uid, password, 'account.move', 'search_read',
                             [[('move_type', 'in', ['out_invoice', 'out_refund'])]],  # 'out_invoice' = Factura, 'out_refund' = Factura rectificativa
                             {'fields': ['id','move_type','invoice_date', 'partner_id','currency_rate']})
    invoice_aux_df = pd.DataFrame(invoices)

    sale_line_ids = milestone_df.sale_line_db_id.dropna().unique().tolist()
    sale_line_ids = [int(x) for x in sale_line_ids]

    account_move_line = models.execute_kw(db, uid, password,
            'account.move.line', 'search_read',
            [[('sale_line_ids', 'in', sale_line_ids)]], {'fields': ['sale_line_ids','move_id','date','currency_id','amount_currency']})

    milestone_invoice_df = pd.DataFrame(account_move_line)

    milestone_invoice_df['move_id'] = milestone_invoice_df['move_id'].apply(lambda x: x if isinstance(x, list) else [None, None])
    milestone_invoice_df[['move_db_id', 'move_name']] = pd.DataFrame(milestone_invoice_df['move_id'].tolist(), index=milestone_invoice_df.index)


    milestone_invoice_df['sale_line_id'] = milestone_invoice_df['sale_line_ids'].apply(lambda x: x[0])
    milestone_invoice_df['invoice_amount'] = -milestone_invoice_df['amount_currency']

    milestone_invoice_df['currency_id'] = milestone_invoice_df['currency_id'].apply(lambda x: x if isinstance(x, list) else [None, None])
    milestone_invoice_df[['currency_db_id', 'invoice_currency_name']] = pd.DataFrame(milestone_invoice_df['currency_id'].tolist(), index=milestone_invoice_df.index)

    milestone_invoice_df.rename(columns={'date':'invoice_date'}, inplace=True)

    milestone_invoice_df = (milestone_invoice_df
                            .set_index('move_db_id')
                            .join(invoice_aux_df[['id','currency_rate']].set_index('id'))
                            .reset_index()
                            )

    milestone_invoice_df = milestone_invoice_df[['sale_line_id','invoice_date','invoice_currency_name','currency_rate','invoice_amount']]
    milestone_invoice_df.set_index('sale_line_id', inplace=True)

    milestone_df = (milestone_df
                    .set_index('sale_line_db_id')
                    .join(milestone_invoice_df)
                    .reset_index()
    )

    milestone_df['invoice_date'] = pd.to_datetime(milestone_df['invoice_date'])
    milestone_df['invoice_month'] = milestone_df['invoice_date'].dt.strftime('%m-%Y')

    return milestone_df

def filter_df(milestone_df, analysis_date_datetime):
    analysis_milestone_df = (
    milestone_df
    # Filtrar filas donde 'date_to' es mayor o igual a 'today'
    .loc[(milestone_df['date_to'] >= analysis_date_datetime.date())
         & (~milestone_df['name'].str.upper().str.contains('SOPORTE', na=False))
         & (~milestone_df['project_name'].str.upper().str.contains('EVOLUTIVO', na=False))
         & (~milestone_df['project_name'].str.upper().str.contains('SOPORTE', na=False))
         ]
    # Seleccionar las columnas necesarias
    [['name', 'project_name', 'date_from', 'date_to',
      'sale_currency_name', 'sale_price_subtotal',
      'invoice_currency_name', 'invoice_amount']]
    # Eliminar filas donde 'sale_price_subtotal' es NaN
    .dropna(subset=['sale_price_subtotal'])
    .fillna(value={'invoice_amount':0, 'invoice_currency_name':''})
    # Agrupar por las columnas especificadas y agregar
    .groupby(['name', 'project_name', 'date_from', 'date_to',
              'sale_currency_name', 'invoice_currency_name'], as_index=False)
    .agg(
        sale_price_subtotal=('sale_price_subtotal', 'max'),
        invoice_amount=('invoice_amount', 'sum')
    )
    # Calcular 'amount_to_invoice' y 'days_to_invoice'
    .assign(
        amount_to_invoice=lambda df: df['sale_price_subtotal'] - df['invoice_amount'],
        percentage_to_invoice=lambda df: 1- (df['invoice_amount'] / df['sale_price_subtotal']),
        days_to_invoice=lambda df: pd.to_timedelta(df['date_to'] - datetime.today().date()).dt.days,
    )
    # Filtrar donde 'amount_to_invoice' es mayor que 0
    # .query('amount_to_invoice > 0')
    # Ordenar por 'days_to_invoice' y 'project_name'
    .sort_values(['days_to_invoice', 'project_name'])
    # Resetear el índice
    .reset_index(drop=True)
    )

    return analysis_milestone_df[analysis_milestone_df['percentage_to_invoice'] > 0]
    # return analysis_milestone_df

def create_milestone_msg(df):
  delayed_invoice_msg = f"{df['name'].upper()}, queda facturar un {round(df['percentage_to_invoice'] * 100, 2)}%"
  to_invoice_msg = f"{df['name'].upper()}, vence {'en ' + str(df['days_to_invoice']) + ' días' if df['days_to_invoice'] != 0 else 'hoy' } y queda facturar un {round(df['percentage_to_invoice'] * 100, 2)}%"
  if df['days_to_invoice'] < 0:
    return delayed_invoice_msg
  else:
    return to_invoice_msg

def send_message(df):
    file_id = os.getenv("FILE_ID_WEBHOOKS")
    # URL pública del archivo de Google Sheets
    sheet_url = f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv'

    # Hacer la solicitud HTTP
    response = requests.get(sheet_url, timeout=20)

    # Verificar que la solicitud fue exitosa
    if response.status_code == 200:
        # Obtener el contenido del CSV como texto
        response_csv = response.text
    
        # Usar StringIO para tratar el string como un archivo
        csv_data = StringIO(response_csv)
        
        # Leer el CSV en un DataFrame
        data_df = pd.read_csv(csv_data)

        discord_map = data_df.set_index('project')['webhook'].to_dict()
        project_users = json.loads(os.getenv("DISCORD_ROLES")).get('project')
        dev_users = json.loads(os.getenv("DISCORD_ROLES")).get('dev')

        for project in project_list:
            msg = ''
            proj_df = df[df['project_name'] == project]
            project_name = proj_df['project_name'].values[0].strip()
            url_webhook = discord_map.get(project_name)
            if url_webhook:
                msg = f"<@&{project_users}> <@&{dev_users}> Hola amigos de {project_name}! ¡Espero que estén muy bien! \n"
                msg += f"Queríamos recordarles que: \n"
                expired_milestone_msg = proj_df[proj_df['days_to_invoice'] < 0].message.values
                not_expired_milestone_msg = proj_df[proj_df['days_to_invoice'] >= 0].message.values
                if expired_milestone_msg.any():
                    msg += "Uno o más hitos en el proyecto han alcanzado su fecha de vencimiento y necesitabamos saber si podemos proceder con la facturación correspondiente. \n \n"
                    formatted_milestones = "\n".join(f"- {milestone}" for milestone in expired_milestone_msg)
                    msg += f"Los hitos vencidos son: \n {formatted_milestones} \n \n"

                if not_expired_milestone_msg.any() and expired_milestone_msg.any():
                    msg += "Ademas, algunas "
                else:
                    msg += "Algunas "

                if not_expired_milestone_msg.any():
                    msg += "fechas de cumplimiento de próximos hitos se están acercando. Agradecemos que realicen las revisiones necesarias para saber si estamos en camino o es necesario revisar fechas. \n \n"
                    formatted_milestones = "\n".join(f"- {milestone}" for milestone in not_expired_milestone_msg)
                    msg += f"Los hitos próximos a cumplirse son: \n {formatted_milestones} \n \n"

                msg += "Si encuentran algún obstáculo o necesitan asistencia adicional, por favor no duden en contactarnos para asegurar un avance fluido. \n"
                msg += 'Gracias por el compromiso y atención de siempre. \nDpto. Gestión'

                print(msg)

                data = {
                "content": msg,
                "username": "Project Reminder"
                }
                requests.post(url_webhook, json=data)
    else:
        print(f"Error al descargar el archivo: {response.status_code}")

analysis_date = '2024-01-01'
analysis_date_datetime = datetime.strptime(analysis_date, "%Y-%m-%d")

models, db, uid, password = connect_odoo()

milestone_df = get_milestone_df(models, db, uid, password)

df = filter_df(milestone_df, analysis_date_datetime)

# Armado del BOT
project_list = df.project_name.unique()
df['message'] = df.apply(create_milestone_msg, axis=1)
send_message(df)


df.to_excel('df.xlsx', index=False) 