import os
import asyncio
import edge_tts

# Mapeo de carpetas de idiomas a voces femeninas de edge-tts
# Se eligen voces femeninas adultas/maduras cuando es posible (ej: Aria en lugar de Jenny).
VOICES = {
    'Aleman': 'de-DE-KatjaNeural',
    'Arabic': 'ar-SA-ZariyahNeural',
    'Bengali': 'bn-IN-TanishaaNeural',
    'Czech': 'cs-CZ-VlastaNeural',
    'Danes': 'da-DK-ChristelNeural',
    'Dutch': 'nl-NL-ColetteNeural',
    'English': 'en-US-AriaNeural',
    'Español_España': 'es-ES-ElviraNeural',
    'ESPANOL_LATAM': 'es-MX-DaliaNeural',
    'Filipino': 'fil-PH-BlessicaNeural',
    'French': 'fr-FR-DeniseNeural',
    'Greek': 'el-GR-AthinaNeural',
    'Hindi': 'hi-IN-SwaraNeural',
    'Hungarian': 'hu-HU-NoemiNeural',
    'Indonesian': 'id-ID-GadisNeural',
    'Italiano': 'it-IT-ElsaNeural',
    'Japanese': 'ja-JP-NanamiNeural',
    'Korean': 'ko-KR-SunHiNeural',
    'Malay': 'ms-MY-YasminNeural',
    'Mandarin_china': 'zh-CN-XiaoxiaoNeural',
    'Mandarin_taiwan': 'zh-TW-HsiaoChenNeural',
    'Norwegian': 'nb-NO-PernilleNeural',
    'Persian': 'fa-IR-DilaraNeural',
    'Polish': 'pl-PL-ZofiaNeural',
    'Portugues': 'pt-BR-FranciscaNeural',
    'Russian': 'ru-RU-SvetlanaNeural',
    'Swahili': 'sw-KE-ZuriNeural',
    'Swedish': 'sv-SE-SofieNeural',
    'Tamil': 'ta-IN-PallaviNeural',
    'Thai': 'th-TH-PremwadeeNeural',
    'Turkish': 'tr-TR-EmelNeural',
    'Ukrainian': 'uk-UA-PolinaNeural',
    'Urdu': 'ur-PK-UzmaNeural',
    'Vietnamese': 'vi-VN-HoaiMyNeural',
    'Catalan': 'ca-ES-JoanaNeural',
    'Camboyano': 'km-KH-SreymomNeural',
    # 'Vasco': NO SOPORTADO — edge-tts no tiene voz en Euskera (Basque).
    'Galician': 'gl-ES-SabelaNeural',
    'Nepali': 'ne-NP-HemkalaNeural',
    'Croata': 'hr-HR-GabrijelaNeural',
    'Servio': 'sr-RS-SophieNeural',
    'Eslovenio': 'sl-SI-PetraNeural'
}

# Configuración de los ajustes de voz (opcional)
RATE = "+0%"  # Velocidad normal
VOLUME = "+0%"  # Volumen normal
PITCH = "+0Hz"  # Tono normal

async def generate_audio(text: str, voice: str, output_path: str):
    """Genera el audio usando edge-tts y lo guarda en output_path"""
    communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME, pitch=PITCH)
    await communicate.save(output_path)

async def main():
    base_path = '/Users/user/Desktop/visual/python'
    idiomas_dir = os.path.join(base_path, 'idiomas')
    
    if not os.path.exists(idiomas_dir):
        print(f"Error: La carpeta '{idiomas_dir}' no existe.")
        return

    # Iterar por cada carpeta de idioma
    for folder_name in os.listdir(idiomas_dir):
        folder_path = os.path.join(idiomas_dir, folder_name)
        
        # Saltarse si no es un directorio
        if not os.path.isdir(folder_path):
            continue

        voice = VOICES.get(folder_name)
        if not voice:
            print(f"Advertencia: No se encontró una voz configurada para '{folder_name}'. Saltando...")
            continue
            
        print(f"\n=== Procesando {folder_name} (Voz: {voice}) ===")
        
        # Obtener todos los archivos .txt y ordenarlos numéricamente
        txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        txt_files.sort(key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else 0)

        for filename in txt_files:
            file_path = os.path.join(folder_path, filename)
            
            # Nombre de salida: reemplaza .txt por .mp3
            output_filename = filename.replace('.txt', '.mp3')
            output_path = os.path.join(folder_path, output_filename)
            
            # Evitar reprocesar si el audio ya existe (opcional)
            if os.path.exists(output_path):
                print(f"  El archivo '{output_filename}' ya existe. Saltando...")
                continue
                
            print(f"  Generando audio para '{filename}' -> '{output_filename}'...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                
            if not text:
                print(f"  El archivo '{filename}' está vacío. Saltando...")
                continue
                
            try:
                await generate_audio(text, voice, output_path)
            except Exception as e:
                print(f"  [Error] No se pudo generar audio para {filename}: {e}")

    print("\n¡Proceso de generación de audios completado!")

if __name__ == '__main__':
    # edge-tts requiere asyncio
    asyncio.run(main())
