from flask import Flask, request, jsonify
import random
import uuid
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Configuración de la base de datos MySQL
DATABASE_CONFIG = {
    'host': 'junction.proxy.rlwy.net',
    'port': '41945',
    'user': 'root',
    'password': 'DkyrMTYoJaolexCjKcgkudUzDOnBHNlb',
    'database': 'railway'
}

# Función para conectar a la base de datos
def get_db_connection():
    return mysql.connector.connect(**DATABASE_CONFIG)

# Inicializar la base de datos (sólo si no existe la tabla)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS boletas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            boleta_id VARCHAR(255),
            banco_id VARCHAR(255),
            nombre VARCHAR(255),
            dni VARCHAR(20),
            empresa VARCHAR(255),
            ruc VARCHAR(20),
            fecha_emision DATE,
            fecha_vencimiento DATE,
            importe FLOAT,
            tea FLOAT,
            dias_calculados INT,
            te FLOAT,
            tasa_descuento FLOAT,
            valor_neto FLOAT,
            comision_estudios FLOAT,
            comision_activacion FLOAT,
            seguro_desgravamen FLOAT,
            costos_adicionales FLOAT,
            valor_recibido FLOAT,
            tcea FLOAT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Inicializar la base de datos
init_db()

# Función para convertir fecha de DD/MM/YYYY a YYYY-MM-DD
def convertir_fecha(fecha):
    return datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")

# Funciones para cálculos (idénticas a las que has proporcionado anteriormente)
def generar_tea(banco_id):
    if banco_id == "BCP":
        return round(random.uniform(15, 25), 2) / 100
    elif banco_id == "Interbank":
        return round(random.uniform(18, 28), 2) / 100
    elif banco_id == "BBVA":
        return round(random.uniform(20, 30), 2) / 100
    else:
        return None

def calcular_dias(fecha_emision, fecha_vencimiento):
    fecha_emision = datetime.strptime(fecha_emision, "%d/%m/%Y")
    fecha_vencimiento = datetime.strptime(fecha_vencimiento, "%d/%m/%Y")
    return (fecha_vencimiento - fecha_emision).days

def calcular_te(tea, dias_calculados):
    if dias_calculados == 0:
        return 0
    return ((1 + tea) ** (dias_calculados / 360) - 1) / dias_calculados

def calcular_tasa_descuento(te):
    return te / (1 + te)

def calcular_valor_neto(importe, tasa_descuento):
    return importe * (1 - tasa_descuento)

def calcular_costos_adicionales(banco_id, importe):
    if banco_id == "BCP":
        comision_estudios = 50.00
        comision_activacion = 30.00
        seguro_desgravamen = importe * 0.015
    elif banco_id == "Interbank":
        comision_estudios = 45.00
        comision_activacion = 35.00
        seguro_desgravamen = importe * 0.017
    elif banco_id == "BBVA":
        comision_estudios = 55.00
        comision_activacion = 25.00
        seguro_desgravamen = importe * 0.016
    else:
        return None, None, None, None
    
    return comision_estudios, comision_activacion, seguro_desgravamen, comision_estudios + comision_activacion + seguro_desgravamen

def calcular_tcea(valor_nominal, valor_recibido, dias_calculados):
    if dias_calculados == 0:
        return 0
    return ((valor_nominal / valor_recibido) ** (360 / dias_calculados)) - 1

# Endpoint para ver todas las boletas
@app.route('/ver_boletas', methods=['GET'])
def ver_boletas():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # dictionary=True para que los resultados se devuelvan como diccionarios
    cursor.execute("SELECT * FROM boletas")
    boletas = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"boletas": boletas}), 200

# Procesar múltiples boletas
@app.route('/procesar_boletas', methods=['POST'])
def procesar_boletas():
    data = request.json
    resultados = []

    # Verificar que se hayan recibido boletas
    if "boletas" not in data:
        return jsonify({"error": "Datos incompletos"}), 400

    # Procesar cada boleta
    for boleta_data in data["boletas"]:
        tea = generar_tea(boleta_data["banco_id"])
        if tea is None:
            continue

        boleta_id = f"{boleta_data['banco_id']}_{uuid.uuid4()}"
        dias_calculados = calcular_dias(boleta_data["fecha_emision"], boleta_data["fecha_vencimiento"])
        te = calcular_te(tea, dias_calculados)
        tasa_descuento = calcular_tasa_descuento(te)
        valor_neto = calcular_valor_neto(boleta_data["importe"], tasa_descuento)
        comision_estudios, comision_activacion, seguro_desgravamen, costos_adicionales = calcular_costos_adicionales(boleta_data["banco_id"], boleta_data["importe"])
        valor_recibido = valor_neto - costos_adicionales
        tcea = calcular_tcea(boleta_data["importe"], valor_recibido, dias_calculados)

        # Convertir las fechas al formato YYYY-MM-DD
        fecha_emision = convertir_fecha(boleta_data["fecha_emision"])
        fecha_vencimiento = convertir_fecha(boleta_data["fecha_vencimiento"])

        # Guardar en la base de datos MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO boletas (boleta_id, banco_id, nombre, dni, empresa, ruc, fecha_emision, fecha_vencimiento, importe, tea, dias_calculados, te, tasa_descuento, valor_neto, comision_estudios, comision_activacion, seguro_desgravamen, costos_adicionales, valor_recibido, tcea)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            boleta_id, boleta_data["banco_id"], boleta_data["nombre"], boleta_data["dni"],
            boleta_data["empresa"], boleta_data["ruc"], fecha_emision, fecha_vencimiento,
            boleta_data["importe"], tea, dias_calculados, te, tasa_descuento, valor_neto,
            comision_estudios, comision_activacion, seguro_desgravamen, costos_adicionales,
            valor_recibido, tcea
        ))
        conn.commit()
        cursor.close()
        conn.close()

        # Agregar el resultado al JSON de respuesta
        resultados.append({
            "Boleta ID": boleta_id,
            "Banco ID": boleta_data["banco_id"],
            "TEA": round(tea * 100, 2),
            "Dias Calculados": dias_calculados,
            "TE": round(te * 100, 6),
            "Tasa de Descuento": round(tasa_descuento * 100, 6),
            "Valor Neto": round(valor_neto, 2),
            "Comisión de Estudios": round(comision_estudios, 2),
            "Comisión de Activación": round(comision_activacion, 2),
            "Seguro de Desgravamen": round(seguro_desgravamen, 2),
            "Costos Adicionales": round(costos_adicionales, 2),
            "Valor Recibido": round(valor_recibido, 2),
            "TCEA": round(tcea * 100, 2)
        })

    return jsonify({"message": "Boletas procesadas exitosamente", "boletas": resultados}), 200

if __name__ == '__main__':
    app.run(debug=True)
