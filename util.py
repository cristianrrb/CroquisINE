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
        #util.mensaje('Se ajusto el extent del mapa.')
        return True
    except:
        #util.mensaje('** No se ajusto el extent del mapa.')
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



