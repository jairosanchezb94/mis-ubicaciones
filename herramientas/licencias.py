"""Genera la página de licencias de código abierto de Mis Ubicaciones.

Uso: python3 -I licencias.py <clon de la app> <carpeta del export con el .map> <html de salida>

- Paquetes JavaScript: los que están de verdad en el bundle (fuentes del
  sourcemap de Metro), no todo node_modules (mucho es solo de compilación).
- Componentes nativos de iOS: el archivo de reconocimientos que genera CocoaPods.
"""

import glob
import html
import json
import os
import plistlib
import re
import sys
from collections import defaultdict

ubi, export, salida = sys.argv[1], sys.argv[2], sys.argv[3]
PROPIOS = {'MisUbicaciones', 'Atajos', 'mis-ubicaciones'}
NOMBRES_LICENCIA = re.compile(r'^(licen[cs]e|copying|notice)(\.(md|txt|markdown))?$', re.I)


def directorio_paquete(fuente):
    """El directorio del paquete al que pertenece un archivo del bundle."""
    # Metro escribe las rutas relativas al proyecto con una barra delante: «/node_modules/…».
    ruta = fuente if os.path.exists(fuente) else os.path.join(ubi, fuente.lstrip('/'))
    ruta = os.path.normpath(ruta)
    trozos = ruta.split(os.sep)
    if 'node_modules' not in trozos:
        return None
    i = len(trozos) - 1 - trozos[::-1].index('node_modules')
    if i + 1 >= len(trozos):
        return None
    fin = i + 3 if trozos[i + 1].startswith('@') else i + 2
    return os.sep.join(trozos[:fin])


def texto_licencia(directorio):
    textos = []
    for nombre in sorted(os.listdir(directorio)):
        if NOMBRES_LICENCIA.match(nombre):
            with open(os.path.join(directorio, nombre), encoding='utf-8', errors='replace') as f:
                textos.append(f.read().strip())
    return '\n\n'.join(textos)


MIT = """MIT License

Copyright (c) {autor}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


def texto_alternativo(info, licencia):
    """Para paquetes sin archivo de licencia: la de su repositorio o la MIT con su autor."""
    nombre = info.get('name', '')
    if nombre.startswith('@react-native/'):
        origen = os.path.join(ubi, 'node_modules', 'react-native', 'LICENSE')
    elif nombre.startswith('expo'):
        origen = os.path.join(ubi, 'node_modules', 'expo', 'LICENSE')
    else:
        origen = None
    if origen and os.path.isfile(origen):
        with open(origen, encoding='utf-8') as f:
            return f.read().strip()
    autor = info.get('author')
    if isinstance(autor, dict):
        autor = autor.get('name')
    if licencia == 'MIT' and autor:
        return MIT.format(autor=re.sub(r'\s*<[^>]*>', '', autor).strip())
    return ''


def licencia_de(info):
    licencia = info.get('license') or info.get('licenses')
    if isinstance(licencia, dict):
        licencia = licencia.get('type')
    if isinstance(licencia, list):
        licencia = ' / '.join(l.get('type', '?') if isinstance(l, dict) else str(l) for l in licencia)
    return licencia or 'Sin indicar'


# --- JavaScript ---------------------------------------------------------------
fuentes = set()
for mapa in glob.glob(os.path.join(export, '**', '*.map'), recursive=True):
    with open(mapa, encoding='utf-8') as f:
        fuentes.update(json.load(f).get('sources', []))

paquetes = {}
for fuente in fuentes:
    directorio = directorio_paquete(fuente)
    if not directorio or directorio in paquetes:
        continue
    manifiesto = os.path.join(directorio, 'package.json')
    if not os.path.isfile(manifiesto):
        continue
    with open(manifiesto, encoding='utf-8') as f:
        info = json.load(f)
    if info.get('name') in PROPIOS:
        continue
    licencia = licencia_de(info)
    paquetes[directorio] = {
        'nombre': info.get('name', os.path.basename(directorio)),
        'version': info.get('version', ''),
        'licencia': licencia,
        'texto': texto_licencia(directorio) or texto_alternativo(info, licencia),
    }

# Una entrada por nombre y versión (el mismo paquete puede estar en varias rutas).
js = {}
for p in paquetes.values():
    js[(p['nombre'], p['version'])] = p
js = sorted(js.values(), key=lambda p: p['nombre'].lower())

# --- Nativo (CocoaPods) ---------------------------------------------------------
reconocimientos = glob.glob(
    os.path.join(ubi, 'ios', 'Pods', 'Target Support Files', 'Pods-*', 'Pods-*-acknowledgements.plist')
)
pods = []
if reconocimientos:
    with open(reconocimientos[0], 'rb') as f:
        for entrada in plistlib.load(f).get('PreferenceSpecifiers', []):
            titulo = entrada.get('Title', '')
            texto = (entrada.get('FooterText') or '').strip()
            if not titulo or titulo in PROPIOS or titulo.startswith('Acknowledgements') or not texto:
                continue
            if titulo == 'Generated by CocoaPods - https://cocoapods.org':
                continue
            pods.append({'nombre': titulo, 'licencia': entrada.get('License', 'Sin indicar'), 'texto': texto})
pods.sort(key=lambda p: p['nombre'].lower())

# Dependencias que React Native compila dentro de su framework precompilado
# (ReactNativeDependencies): sus textos se descargan de cada repositorio oficial.
EXTRA = [
    ('Folly', 'Apache-2.0', 'folly'),
    ('Boost', 'BSL-1.0', 'boost'),
    ('glog', 'BSD-3-Clause', 'glog'),
    ('double-conversion', 'BSD-3-Clause', 'double-conversion'),
    ('{fmt}', 'MIT', 'fmt'),
    ('fast_float', 'MIT', 'fast_float'),
    ('SocketRocket', 'BSD', 'SocketRocket'),
]
carpeta_extra = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'licencias-extra')
dependencias_rn = []
for nombre, licencia, archivo in EXTRA:
    with open(os.path.join(carpeta_extra, f'{archivo}.txt'), encoding='utf-8') as f:
        dependencias_rn.append({'nombre': nombre, 'licencia': licencia, 'texto': f.read().strip()})


# --- HTML -------------------------------------------------------------------------
def bloque(p, con_version=True):
    titulo = html.escape(p['nombre'] + (f" {p['version']}" if con_version and p.get('version') else ''))
    licencia = html.escape(p['licencia'])
    texto = p['texto'] or f"Licencia {p['licencia']}. El paquete no incluye el texto de la licencia."
    return (
        f'      <details>\n        <summary>{titulo} · {licencia}</summary>\n'
        f'        <pre>{html.escape(texto)}</pre>\n      </details>\n'
    )


def resumen(lista):
    cuenta = defaultdict(int)
    for p in lista:
        cuenta[p['licencia']] += 1
    return ', '.join(f'{html.escape(l)} ({n})' for l, n in sorted(cuenta.items(), key=lambda x: -x[1]))


partes = [
    """<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Licencias de código abierto · Mis Ubicaciones</title>
    <meta name="description" content="Componentes de código abierto que incluye Mis Ubicaciones y sus licencias." />
    <link rel="stylesheet" href="../estilo.css" />
    <link rel="icon" href="../icono.png" />
  </head>
  <body>
    <main>
      <a class="app" href="../">
        <img src="../icono.png" alt="" />
        <span>Mis Ubicaciones</span>
      </a>

      <h1>Licencias de código abierto</h1>
      <p>
        Mis Ubicaciones está hecha con componentes de código abierto. Gracias a quienes los
        mantienen. Estos son los que incluye la app, con sus avisos de copyright y sus licencias.
      </p>
""",
    f"""
      <h2>Componentes JavaScript</h2>
      <p class="nota">Los que van dentro de la app, comunes a iPhone y Android: {len(js)} paquetes. {resumen(js)}.</p>
""",
    ''.join(bloque(p) for p in js),
    f"""
      <h2>Componentes nativos de iPhone</h2>
      <p class="nota">Bibliotecas compiladas en la app de iPhone: {len(pods)}. {resumen(pods)}.</p>
""",
    ''.join(bloque(p, con_version=False) for p in pods),
    """
      <h3>Dentro de React Native</h3>
      <p class="nota">Bibliotecas que React Native lleva compiladas en su propio framework.</p>
""",
    ''.join(bloque(p, con_version=False) for p in dependencias_rn),
    """
      <h2>Mapa en Android</h2>
      <p>
        En Android, el mapa usa <a href="https://leafletjs.com/">Leaflet</a> (licencia BSD de 2
        cláusulas, © Volodymyr Agafonkin y CloudMade), que se carga desde unpkg.com, con imágenes de
        mapa de Esri, cuya atribución aparece sobre el propio mapa.
      </p>

      <nav class="pie" aria-label="Más información">
        <a href="../">Ayuda y contacto</a>
        <a href="../privacidad/">Política de privacidad</a>
        <a href="../condiciones/">Condiciones de uso y aviso legal</a>
      </nav>
    </main>
  </body>
</html>
""",
]

with open(salida, 'w', encoding='utf-8') as f:
    f.write(''.join(partes))

sin_texto = [p['nombre'] for p in js if not p['texto']]
print(f'JS: {len(js)} paquetes ({len(sin_texto)} sin texto de licencia: {", ".join(sin_texto[:12])})')
print(f'Nativo: {len(pods)} pods')
print('Licencias JS:', resumen(js))
