"""
Parser de texto.txt: divide el guion en secciones numeradas y normaliza
los títulos a slugs aptos para nombres de archivo.

Ejemplo de entrada (línea de título):
    1 – INTRODUCCIÓN · BIENVENIDA

Salida normalizada:
    numero  = '1'
    titulo  = 'introduccion_bienvenida'
    contenido = '... resto del texto hasta la próxima sección ...'
"""

import re
import unicodedata


# Patrón que reconoce un título de sección:
#   - número al inicio
#   - separador: guion corto '-' o guion largo '–' (puede haber espacios)
#   - resto de la línea = título crudo
SECTION_RE = re.compile(r"^(\d+)\s*[–-]\s*(.+)$")


def normalize_title(raw_title: str) -> str:
    """
    Convierte un título crudo a un slug seguro para nombres de archivo.

    Reglas:
        1. Eliminar acentos (NFKD).
        2. Pasar a minúsculas.
        3. Reemplazar cualquier carácter no alfanumérico por '_'.
        4. Colapsar múltiples '_' en uno solo.
        5. Quitar '_' al inicio y al final.

    Ej:  'INTRODUCCIÓN · BIENVENIDA'   -> 'introduccion_bienvenida'
         'WAT CHAI WATTANARAM'         -> 'wat_chai_wattanaram'
         'LLEGADA A AYUTTHAYA · PRIMERAS IMPRESIONES'
                                       -> 'llegada_a_ayutthaya_primeras_impresiones'
    """
    # 1. Quitar acentos
    nfkd = unicodedata.normalize("NFKD", raw_title)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))

    # 2. A minúsculas
    lower = sin_acentos.lower()

    # 3. Reemplazar todo lo que no sea letra ASCII o dígito por '_'
    slug = re.sub(r"[^a-z0-9]+", "_", lower)

    # 4-5. Colapsar y limpiar '_' sobrantes
    slug = re.sub(r"_+", "_", slug).strip("_")

    return slug


def parse_text_file(path: str) -> dict:
    """
    Lee el archivo de texto y devuelve un diccionario:
        {
            '1': {'titulo': 'introduccion_bienvenida', 'contenido': '...'},
            '2': {'titulo': 'camino_hacia_ayutthaya',  'contenido': '...'},
            ...
        }

    Las claves son los números de sección como string (preservando el orden
    de aparición en el archivo, gracias a que dict mantiene orden de inserción
    desde Python 3.7).
    """
    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read()

    secciones: dict = {}
    seccion_actual = None
    buffer_texto = []

    for linea in contenido.split("\n"):
        match = SECTION_RE.match(linea.strip())
        if match:
            # Cerramos la sección anterior antes de empezar la nueva
            if seccion_actual is not None:
                secciones[seccion_actual]["contenido"] = (
                    "\n".join(buffer_texto).strip()
                )

            numero = match.group(1)
            titulo_crudo = match.group(2).strip()
            seccion_actual = numero
            buffer_texto = []
            secciones[numero] = {
                "titulo": normalize_title(titulo_crudo),
                "titulo_crudo": titulo_crudo,
                "contenido": "",
            }
        else:
            if seccion_actual is not None:
                buffer_texto.append(linea)

    # Cierre de la última sección
    if seccion_actual is not None:
        secciones[seccion_actual]["contenido"] = "\n".join(buffer_texto).strip()

    return secciones


if __name__ == "__main__":
    # Modo de prueba rápido: ejecuta este archivo con:
    #     python text_parser.py texto.txt
    import sys

    archivo = sys.argv[1] if len(sys.argv) > 1 else "texto.txt"
    secs = parse_text_file(archivo)
    print(f"Se encontraron {len(secs)} secciones:\n")
    for num, info in secs.items():
        print(f"  [{num}] {info['titulo']:<50}  ({info['titulo_crudo']})")
