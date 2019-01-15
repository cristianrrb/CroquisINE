# -*- coding: iso-8859-1 -*-

import arcpy
import os, urllib, urllib2, json, sys
import datetime, csv, uuid, zipfile

urlConfiguracion   = 'https://gis.ine.cl/croquis/configuracion.json'

def leeJsonConfiguracion():
    response = urllib.urlopen(urlConfiguracion)
    data = json.loads(response.read())
    return data

def normalizar(s):
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ñ", "n"),
        (" ", "_"),
    )
    for a, b in replacements:
        s = s.replace(a, b).replace(a.upper(), b.upper())
    return s

config = leeJsonConfiguracion()

nombre_region = "MAULE"

nombre_comuna = "Hualañé Chico"
nueva_comuna = normalizar(nombre_comuna)
nombrePDF = "archivo.pdf"

rutaDestino = os.path.join(config['rutabase'],"MUESTRAS_PDF","MUESTRAS_P","ENE",nombre_region,nueva_comuna)
if not os.path.exists(rutaDestino):
    os.makedirs(rutaDestino)

    mxd = arcpy.mapping.MapDocument("CURRENT")
    arcpy.mapping.ExportToPDF(mxd, destinoPDF)
else:
    destinoPDF = os.path.join(rutaDestino, nombrePDF)
    arcpy.mapping.ExportToPDF(mxd, destinoPDF)
