from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import urllib3
import time

app = Flask(__name__)

# --- CONFIGURACIÓN ---
# Ignoramos los errores de certificado SSL (el BCV suele tenerlos vencidos)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- MEMORIA CACHÉ ---
cache = {
    "datos": None,             # Aquí se guardará el JSON
    "ultima_actualizacion": 0  # Aquí guardaremos cuándo fue la última vez
}
TIEMPO_EXPIRACION = 3600       # 1 hora (3600 segundos)

def obtener_tasas_bcv_real():
    """Función que hace el trabajo sucio de ir a la web del BCV"""
    print("🔄 Conectando con el BCV para actualizar datos...")
    url = "https://www.bcv.org.ve/"
    try:
        # Usamos un User-Agent para parecer un navegador real y no un robot
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, verify=False, timeout=15, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # 1. Extraemos los precios
            dolar = soup.find("div", {"id": "dolar"}).find("strong").text.strip()
            euro = soup.find("div", {"id": "euro"}).find("strong").text.strip()
            
            # 2. NUEVO: Extraemos la fecha de valor
            # Buscamos la etiqueta <span class="date-display-single">
            fecha_tag = soup.find("span", {"class": "date-display-single"})
            fecha_texto = fecha_tag.text.strip() if fecha_tag else "Fecha no encontrada"

            def limpiar(texto):
                return float(texto.replace(',', '.'))

            return {
                "fuente": "Banco Central de Venezuela",
                "fecha_valor": fecha_texto,  # <--- Aquí va la fecha extraída
                "timestamp_consulta": time.time(),
                "tasas": {
                    "USD": {
                        "nombre": "Dólar",
                        "valor": limpiar(dolar),
                        "simbolo": "$"
                    },
                    "EUR": {
                        "nombre": "Euro",
                        "valor": limpiar(euro),
                        "simbolo": "€"
                    }
                }
            }
    except Exception as e:
        print(f"Error scraping: {e}")
        return None

# --- RUTAS DE LA API ---

@app.route('/')
def index():
    """Ruta para la página principal (evita el error 404 Not Found)"""
    return jsonify({
        "mensaje": "¡Tu API del BCV está funcionando!",
        "instruccion": "Para ver los precios, ve a: /api/tasas"
    })

@app.route('/api/tasas', methods=['GET'])
def get_tasas():
    ahora = time.time()
    
    # Lógica de Caché:
    # Si está vacío O si ya pasó 1 hora (3600 seg), actualizamos.
    if cache["datos"] is None or (ahora - cache["ultima_actualizacion"] > TIEMPO_EXPIRACION):
        nuevos_datos = obtener_tasas_bcv_real()
        
        if nuevos_datos:
            cache["datos"] = nuevos_datos
            cache["ultima_actualizacion"] = ahora
        else:
            # Si el BCV falla, intentamos devolver el dato viejo si existe
            if cache["datos"] is None:
                return jsonify({"error": "El sitio del BCV no responde y no hay caché"}), 503
    
    # Devolvemos la respuesta
    return jsonify({
        "data": cache["datos"],
        "cached": True, # Indica que la respuesta viene rápida de memoria
        "segundos_para_proxima_actualizacion": int(TIEMPO_EXPIRACION - (ahora - cache["ultima_actualizacion"]))
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
