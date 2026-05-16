import os
import re
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Error: La librería 'deep-translator' no está instalada.")
    print("Por favor, instálala ejecutando: pip install deep-translator")
    exit(1)

def main():
    # Ruta base del proyecto
    base_path = '/Users/user/Desktop/visual/python'
    input_file = os.path.join(base_path, 'texto.txt')
    
    # Lista de idiomas a los que se traducirá.
    # El formato es 'código_idioma': 'Nombre_Carpeta'
    # Puedes añadir o quitar idiomas de esta lista según necesites.
    idiomas = [
        ('de', 'Aleman'),
        ('ar', 'Arabic'),
        ('bn', 'Bengali'),
        ('cs', 'Czech'),
        ('da', 'Danes'),
        ('nl', 'Dutch'),
        ('en', 'English'),
        ('es', 'Español_España'),
        ('es', 'ESPANOL_LATAM'),
        ('tl', 'Filipino'),
        ('fr', 'French'),
        ('el', 'Greek'),
        ('hi', 'Hindi'),
        ('hu', 'Hungarian'),
        ('id', 'Indonesian'),
        ('it', 'Italiano'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
        ('ms', 'Malay'),
        ('zh-CN', 'Mandarin_china'),
        ('zh-TW', 'Mandarin_taiwan'),
        ('no', 'Norwegian'),
        ('fa', 'Persian'),
        ('pl', 'Polish'),
        ('pt', 'Portugues'),
        ('ru', 'Russian'),
        ('sw', 'Swahili'),
        ('sv', 'Swedish'),
        ('ta', 'Tamil'),
        ('th', 'Thai'),
        ('tr', 'Turkish'),
        ('uk', 'Ukrainian'),
        ('ur', 'Urdu'),
        ('vi', 'Vietnamese'),
        ('ca', 'Catalan'),
        ('km', 'Camboyano'),
        ('eu', 'Vasco'),
        ('gl', 'Galician'),
        ('ne', 'Nepali'),
        ('hr', 'Croata'),
        ('sr', 'Servio'),
        ('sl', 'Eslovenio')
    ]
    
    # Leer el archivo original
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"No se pudo encontrar el archivo: {input_file}")
        return

    # Dividir el texto en secciones
    # Expresión regular para detectar los títulos (ej: "1 – INTRODUCCIÓN · BIENVENIDA")
    lines = content.split('\n')
    secciones = {}
    seccion_actual = None
    texto_actual = []
    
    for line in lines:
        # Busca un número al principio, seguido de un guión (corto o largo)
        match = re.match(r'^(\d+)\s*[–-]\s*.*$', line.strip())
        if match:
            # Si ya estábamos en una sección, guardamos su contenido
            if seccion_actual is not None:
                # Unimos las líneas y quitamos espacios extra al principio/final
                secciones[seccion_actual] = '\n'.join(texto_actual).strip()
            
            # Empezamos una nueva sección
            seccion_actual = match.group(1)
            texto_actual = []
        else:
            # Si no es un título, es contenido de la sección actual
            if seccion_actual is not None:
                texto_actual.append(line)
                
    # Guardar la última sección
    if seccion_actual is not None:
        secciones[seccion_actual] = '\n'.join(texto_actual).strip()
        
    print(f"Se encontraron {len(secciones)} secciones. Iniciando traducciones...\n")

    # Crear carpeta principal para todos los idiomas
    output_base_dir = os.path.join(base_path, 'idiomas')
    os.makedirs(output_base_dir, exist_ok=True)

    # Procesar cada idioma
    for codigo_idioma, nombre_carpeta in idiomas:
        # Crear la carpeta para el idioma dentro de la carpeta 'idiomas'
        lang_dir = os.path.join(output_base_dir, nombre_carpeta)
        os.makedirs(lang_dir, exist_ok=True)
        print(f"=== Traduciendo al {nombre_carpeta} ({codigo_idioma}) ===")
        
        # Inicializar el traductor para el idioma destino
        translator = GoogleTranslator(source='auto', target=codigo_idioma)
        
        for num_seccion, texto in secciones.items():
            if not texto:
                continue
                
            print(f"  Traduciendo sección {num_seccion}...")
            
            try:
                # Traducir el texto. GoogleTranslator soporta hasta 5000 caracteres por petición.
                texto_traducido = translator.translate(texto)
            except Exception as e:
                print(f"  [Error] No se pudo traducir la sección {num_seccion}: {e}")
                texto_traducido = texto # En caso de error, guardar el texto original
                
            # Guardar en su respectivo archivo
            output_file = os.path.join(lang_dir, f"{num_seccion}.txt")
            with open(output_file, 'w', encoding='utf-8') as out_f:
                out_f.write(texto_traducido)
                
    print("\n¡Proceso de traducción y generación de archivos completado!")

if __name__ == '__main__':
    main()
