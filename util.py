# -*- coding: iso-8859-1 -*-
import arcpy
import datetime
import urllib
import urllib2
import json
import os
import uuid
import zipfile
import sys

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
            mensaje("Extension del poligono obtenida correctamente.")
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
        mensaje("Ruta ZIP {}".format(rutaZip))
        with zipfile.ZipFile(rutaZip, 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(rutaCSV, os.path.basename(rutaCSV))

            listaPDFs = [r.rutaPDF for r in registros if r.rutaPDF != ""]
            for archivo in listaPDFs:
                mensaje("Comprimiendo {}".format(os.path.basename(archivo)))
                myzip.write(archivo, os.path.basename(archivo))
        return rutaZip
    except:
        return None

def calculaDistanciaBufferManzana(area):
    #print
    return '15 Meters'

def calculaDistanciaBufferRAU(area):
    if area <= 210000:     # 0 .. 210000
        return '15 Meters'
    if area > 210000:      # 210000 ..
        return '30 Meters'

def calculaDistanciaBufferRural(area):
    if area <= 932000:      # 0 .. 932000
        #return '50 Meters'
        return '20 Meters'
    if area <= 1000000:     # 932000 .. 1000000  # VALIDAR ESTE VALOR
        #return '150 Meters'
        return '50 Meters'
    #return '500 Meters'     # valor por defecto
    return '100 Meters'     # valor por defecto

def generaListaCodigos(texto):
    try:
        lista = texto.split(",")
        listaNumeros = [int(x) for x in lista]
        return listaNumeros
    except:
        return []

def areasExcluidas(poligono, url):
    try:
        poly_paso = poligono.buffer(10)
        poli = arcpy.Polygon(poly_paso.getPart(0), poligono.spatialReference)
        params = {'f':'json', 'where':'1=1', 'outFields':'SHAPE',  'geometry':poli.JSON, 'geometryType':'esriGeometryPolygon',
                  'spatialRel':'esriSpatialRelContains', 'inSR':'WGS_1984_Web_Mercator_Auxiliary_Sphere',
                  'outSR':'WGS_1984_Web_Mercator_Auxiliary_Sphere'}
        queryURL = "{}/query".format(url)
        req = urllib2.Request(queryURL, urllib.urlencode(params))
        response = urllib2.urlopen(req)
        ids = json.load(response)
        pols = []
        poly = poli.buffer(-10)
        for pol in ids["features"]:
            polygon = arcpy.AsShape(pol["geometry"], True)
            mensaje(poly.contains(polygon, "PROPER"))
            if poly.contains(polygon, "PROPER"):
                pols.append(polygon)
        if len(pols) > 0:
            mensaje(len(pols))
            return pols
        else:
            return None
    except:
        mensaje('** Error en areas de exclusion.')
    return ""

def intersectaConArea(poligono, urlServicio):
    try:
        queryURL = "{}/query".format(urlServicio)
        params = {'token':self.token, 'f':'json', 'where':'1=1', 'outFields':'*', 'returnIdsOnly':'true', 'geometry':poligono.JSON, 'geometryType':'esriGeometryPolygon'}
        req = urllib2.Request(queryURL, urllib.urlencode(params))
        response = urllib2.urlopen(req)
        ids = json.load(response)
        if ids['objectIds'] != None:
            return "Si"
    except:
        pass
    return "No"

def descomponeManzent(codigo):
    c = "{}".format(codigo)
    cut = c[:-9]
    dis = c[-9:-7]
    area = c[-7:-6]
    loc = c[-6:-3]
    ent = c[-3:]
    return cut, dis, area, loc, ent

def limpiaEsquicio(mxd, capa, campo, valor):
    try:
        mensaje("Limpieza de esquicio iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[1]
        lyr = arcpy.mapping.ListLayers(mxd, capa, df)[0]
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyr.dataSource, campo), valor)
        lyr.definitionQuery = sql_exp
        mensaje(sql_exp)
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de esquicio.")
    return None

def cortaEtiqueta(mxd, elLyr, poly):
    try:
        path_scratchGDB = arcpy.env.scratchGDB
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr_sal = os.path.join("in_memory", elLyr)
        lyr = arcpy.mapping.ListLayers(mxd, elLyr, df)[0]
        mensaje("Layer encontrado {}".format(lyr.name))
        arcpy.SelectLayerByLocation_management(lyr, "INTERSECT", poly, "", "NEW_SELECTION")
        arcpy.Clip_analysis(lyr, poly, lyr_sal)
        cuantos = int(arcpy.GetCount_management(lyr_sal).getOutput(0))
        if cuantos > 0:
            if arcpy.Exists(os.path.join(path_scratchGDB, elLyr)):
                arcpy.Delete_management(os.path.join(path_scratchGDB, elLyr))
            arcpy.CopyFeatures_management(lyr_sal, os.path.join(path_scratchGDB, elLyr))
            lyr.replaceDataSource(path_scratchGDB, 'FILEGDB_WORKSPACE', elLyr , True)
            mensaje("Etiquetas correcta de {}".format(elLyr))
        else:
            mensaje("No hay registros de {}".format(elLyr))
        return True
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en preparacion de etiquetas.")
    return False

class Registro:
    def __init__(self, codigo):
        self.hora = "{}".format(datetime.datetime.now().strftime("%H:%M:%S"))
        self.codigo = codigo
        self.estado = ""
        self.motivo = ""
        # variables analisis manzanas
        self.intersectaPE = ""
        self.intersectaCRF = ""
        self.intersectaAV = ""
        self.homologacion = ""
        self.estadoSuperficie = ""
        self.motivoSuperficie = ""
        self.area_manzana2016 = ""
        self.area_manzana2017 = ""
        self.estadoViviendas = ""
        self.motivoViviendas = ""
        # variables analisis manzanas
        self.codigoBarra = ""
        self.formato = ""
        self.orientacion = ""
        self.escala = ""
        self.rutaPDF = ""

class Diccionario:
    def __init__(self, config):
        self.dictRegiones   = {r['codigo']:r['nombre'] for r in config['regiones']}
        self.dictProvincias = {r['codigo']:r['nombre'] for r in config['provincias']}
        self.dictComunas    = {r['codigo']:r['nombre'] for r in config['comunas']}
        self.dictUrbano = {}

    def nombreRegion(self, codigo):
        if self.dictRegiones.has_key(codigo):
            return self.dictRegiones[codigo].encode('utf8')
        else:
            return codigo

    def nombreProvincia(self, codigo):
        if self.dictProvincias.has_key(codigo):
            return self.dictProvincias[codigo].encode('utf8')
        else:
            return codigo

    def nombreComuna(self, codigo):
        if self.dictComunas.has_key(codigo):
            return self.dictComunas[codigo].encode('utf8')
        else:
            return codigo

    def nombreUrbano(self, codigo):
        if self.dictUrbano.has_key(codigo):
            return self.dictUrbano[codigo].encode('utf8')
        else:
            return codigo

class InfoMarco:
    def __init__(self, codigo, config):
        self.urlManzanas = ''
        self.urlSecciones_RAU = ''
        self.urlSecciones_Rural = ''
        self.urlComunas = ''
        self.urlLUC = ''
        self.urlAreaDestacada = ''
        self.urlManzanasCenso2017 = ''
        self.urlPE = ''
        self.urlCRF = ''
        self.urlAV = ''
        self.urlHomologacion = ''
        self.nombreCampoIdHomologacion = "MANZENT_MM2014"
        self.nombreCampoTipoHomologacion = "TIPO_HOMOLOGACIï¿½N"
        self.nombreCampoTotalViviendas = "TOT_VIV_PART_PC2016"
        self.leeConfiguracion(codigo, config)

    def leeConfiguracion(self, codigo, config):
        for marco in config['marcos']:
            if marco['id'] == codigo:
                self.urlManzanas          = marco['config']['urlManzanas']
                self.urlSecciones_RAU     = marco['config']['urlSecciones_RAU']
                self.urlSecciones_Rural   = marco['config']['urlSecciones_Rural']
                self.urlComunas           = marco['config']['urlComunas']
                self.urlLUC               = marco['config']['urlLUC']
                self.urlAreaDestacada     = marco['config']['urlAreaDestacada']
                self.urlManzanasCenso2017 = marco['config']['urlManzanasCenso2017']
                self.urlPE  = marco['config']['urlPE']
                self.urlAV  = marco['config']['urlAV']
                self.urlCRF = marco['config']['urlCRF']
                self.urlHomologacion = marco['config']['urlHomologacion']
                self.nombreCampoIdHomologacion   = marco['config']['nombreCampoIdHomologacion']
                self.nombreCampoTipoHomologacion = marco['config']['nombreCampoTipoHomologacion']
                self.nombreCampoTotalViviendas   = marco['config']['nombreCampoTotalViviendas']

class GeneraPDF:
    def __init__(self, config, dic, parametros):
        self.config = config
        self.dic = dic
        self.parametros = parametros

    def generaRutaPDF(self, nombrePDF, datos):
        try:
            nueva_region = self.normalizaPalabra(self.dic.nombreRegion(datos[2]))
            nueva_comuna = self.normalizaPalabra(self.dic.nombreComuna(datos[4]))

            if self.parametros.Estrato == "Rural":
                rutaDestino = os.path.join(self.config['rutabase'], "MUESTRAS_PDF", self.parametros.Encuesta, nueva_region, nueva_comuna)
            else:
                nueva_urbano = self.normalizaPalabra(self.dic.nombreUrbano(datos[5]))
                rutaDestino = os.path.join(self.config['rutabase'], "MUESTRAS_PDF", self.parametros.Encuesta, nueva_region, nueva_comuna, nueva_urbano)

            if not os.path.exists(rutaDestino):
                os.makedirs(rutaDestino)

            destinoPDF = os.path.join(rutaDestino, nombrePDF)
            mensaje("Se creo la ruta de destino PDF")
            return destinoPDF
        except:
            mensaje("No se pudo crear el destino PDF")
            return None

    def generaPDF(self, mxd, destinoPDF):
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

            arcpy.mapping.ExportToPDF(mxd, destinoPDF, data_frame, df_export_width, df_export_height, resolution, image_quality, color_space, compress_vectors, image_compression, picture_symbol, convert_markers, embed_fonts, layers_attributes,georef_info,jpeg_compression_quality)
            mensaje("Croquis Exportado a pdf")

            return destinoPDF
        except Exception:
            mensaje(sys.exc_info()[1].args[0])
            mensaje("No se pudo exportar Croquis a pdf")
            return None

    def normalizaPalabra(self, s):
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
