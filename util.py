# -*- coding: iso-8859-1 -*-
import arcpy
import datetime
import urllib
import json
import os
import uuid

def mensaje(m):
    n = datetime.datetime.now()
    s = "[{}]: {}".format(n.strftime("%H:%M:%S"), m)
    print(s)
    arcpy.AddMessage(s)

def obtieneToken(usuario, clave, urlPortal):
    params = {'username':usuario, 'password':clave, 'client':'referer', 'referer':urlPortal, 'expiration':600, 'f':'json'}
    urlToken = urlPortal + '/sharing/rest/generateToken?'
    response = urllib.urlopen(urlToken, urllib.urlencode(params)).read()
    try:
        jsonResponse = json.loads(response)
        if 'token' in jsonResponse:
            mensaje('Token obtenido correctamente.')
            return jsonResponse['token']
        elif 'error' in jsonResponse:
            mensaje(jsonResponse['error']['message'])
            for detail in jsonResponse['error']['details']:
                mensaje('Error en obtieneToken: ' + detail)
    except:
        mensaje('** Error en obtieneToken.')
    return None

def zoom(mxd, extent, escala):
    try:
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        newExtent = df.extent
        newExtent.XMin, newExtent.YMin = extent.XMin, extent.YMin
        newExtent.XMax, newExtent.YMax = extent.XMax, extent.YMax
        df.extent = newExtent
        df.scale = escala
        mensaje('Se ajusto el extent del mapa.')
        return True
    except:
        mensaje('** No se ajusto el extent del mapa.')
        return False

def zoomEsquicio(mxd, extent):
    try:
        df = arcpy.mapping.ListDataFrames(mxd)[1]
        #util.mensaje(extent)
        newExtent = df.extent
        newExtent.XMin, newExtent.YMin = extent.XMin, extent.YMin
        newExtent.XMax, newExtent.YMax = extent.XMax, extent.YMax
        df.extent = newExtent
        #df.scale = escala
        #util.mensaje('Se ajusto el extent Esquicio del mapa.')
        #return True
    except:
        #util.mensaje('** No se ajusto el extent Esquicio del mapa.')
        return False

def calculaExtent(fs, metrosBuffer):
    try:
        buffer = os.path.join('in_memory', 'buffer_{}'.format(str(uuid.uuid1()).replace("-","")))
        fcBuffer = arcpy.Buffer_analysis(fs, buffer, metrosBuffer)
        with arcpy.da.SearchCursor(fcBuffer, ['SHAPE@']) as rows:
            lista = [r[0] for r in rows]
        arcpy.Delete_management(buffer)
        if lista != None and len(lista) > 0:
            mensaje("Extensión del poligono obtenida correctamente.")
            return lista[0].extent
        else:
            mensaje("No se pudo calcular extension del poligono.")
            return None
    except:
        mensaje("** Error en calculaExtent.")
        return None

def comprime(nombreZip, registros, rutaCSV):
    try:
        rutaZip = os.path.join(arcpy.env.scratchFolder, nombreZip)
        #util.mensaje("Ruta ZIP {}".format(rutaZip))
        with zipfile.ZipFile(rutaZip, 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(rutaCSV, os.path.basename(rutaCSV))

            listaPDFs = [r.rutaPDF for r in registros if r.rutaPDF != ""]
            for archivo in listaPDFs:
                #util.mensaje("Comprimiendo {}".format(os.path.basename(archivo)))
                myzip.write(archivo, os.path.basename(archivo))
        return rutaZip
    except:
        return None

def normalizaPalabra(s):
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ñ", "n"),
        ("Á", "A"),
        ("É", "E"),
        ("Í", "I"),
        ("Ó", "O"),
        ("Ú", "U"),
        ("Ñ", "N"),
        (" ", "_"),
        ("'", ""),
    )
    for a, b in replacements:
        s = s.replace(a, b).replace(a.upper(), b.upper())
    return s

def generaPDF(mxd, nombrePDF, datos, parametros, dic, config):
    try:
        data_frame = 'PAGE_LAYOUT'
        df_export_width = 640 #not actually used when data_fram is set to 'PAGE_LAYOUT'
        df_export_height = 480 #not actually used when data_fram is set to 'PAGE_LAYOUT'
        resolution = 200
        image_quality = 'BETTER' #'BEST' 'FASTER'
        color_space = 'RGB'
        compress_vectors = True
        image_compression = 'ADAPTIVE'
        picture_symbol = 'RASTERIZE_BITMAP'
        convert_markers = True
        embed_fonts = True
        layers_attributes = 'LAYERS_ONLY'
        georef_info = True #Parametro para generar GEOPDF
        jpeg_compression_quality = 80

        # VERIFICA RUTA DE DESTINO DE LOS PLANOS DE UBICACION
        if parametros.SoloPlanoUbicacion != "Si":
            nueva_region = normalizaPalabra(dic.nombreRegion(datos[2]))
            nueva_comuna = normalizaPalabra(dic.nombreComuna(datos[4]))

            if parametros.Estrato == "Rural":
                rutaDestino = os.path.join(config['rutabase'], "MUESTRAS_PDF", parametros.Encuesta, nueva_region, nueva_comuna)
            else:
                nueva_urbano = normalizaPalabra(nombreUrbano(datos[5]))
                mensaje(nueva_urbano)
                rutaDestino = os.path.join(config['rutabase'], "MUESTRAS_PDF", parametros.Encuesta, nueva_region, nueva_comuna, nueva_urbano)
        else:
            rutaDestino = os.path.join(config['rutabase'], "MUESTRAS_PDF", parametros.Encuesta, "PLANOS_UBICACION")

        mensaje(rutaDestino)

        if not os.path.exists(rutaDestino):
            os.makedirs(rutaDestino)

        destinoPDF = os.path.join(rutaDestino, nombrePDF)
        mensaje(destinoPDF)
        arcpy.mapping.ExportToPDF(mxd, destinoPDF, data_frame, df_export_width, df_export_height, resolution, image_quality, color_space, compress_vectors, image_compression, picture_symbol, convert_markers, embed_fonts, layers_attributes,georef_info,jpeg_compression_quality)
        mensaje("Croquis Exportado a pdf")
        return destinoPDF
    except:
        mensaje("No se pudo exportar Croquis a pdf")
        return None

class Registro:
    def __init__(self, codigo):
        self.hora = "{}".format(datetime.datetime.now().strftime("%H:%M:%S"))
        self.codigo = codigo
        self.estado = ""
        self.motivo = ""
        self.intersectaPE = ""
        self.intersectaCRF = ""
        self.intersectaAV = ""
        self.homologacion = ""
        self.codigoBarra = ""
        # Analisis de comparación de superficie de manzanas
        self.estadoSuperficie = ""
        self.motivoSuperficie = ""
        # Analisis de Rechazo por cantidad de viviendas
        self.estadoViviendas = ""
        self.motivoViviendas = ""
        self.formato = ""
        self.orientacion = ""
        self.escala = ""
        self.rutaPDF = ""



