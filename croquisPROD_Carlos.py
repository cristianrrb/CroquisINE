# -*- coding: iso-8859-1 -*-
import arcpy
import os
import urllib
import urllib2
import json
import sys
import datetime
import csv
import uuid
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

dato de comuna codigo nombre de capa

# Obtiene informacion para plano de ubicacion para este ejemplo Rural
# secciones rurales Valdivia ----> 14101900011,14101900021,14101900028,14101900006,14101900004
def obtieneInfoParaPlanoUbicacion(urlEstrato, urlPlano, token):
    try:
        condiciones = []
        for codigo in listaCodigos:
            condicion = "{}+%3D+{}".format(dictCamposId[parametroEstrato], codigo)
            condiciones.append(condicion)

        query = "+OR+".join(condiciones)
        url = '{}/query?token={}&where={}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'

        fs = arcpy.FeatureSet()
        fs.load(url.format(urlEstrato, token, query))

        fc = os.path.join("in_memory", "fc")
        fs.save(fc)

        if parametroEstrato == "Manzana":
            fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT','MANZ']
        elif parametroEstrato == "RAU":
            fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION','CU_SECCION']
        elif parametroEstrato == "Rural":
            fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'CUT', 'COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']

        lista = []
        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if  len(lista) > 0:
            mensaje("** OK en obtieneInfoPara_PlanoUbicacion")
            extent = obtieneExtentComunaPlanoUbicacion(urlPlano, lista[0][0])
            polygonComuna = obtiene_PoligonoComunaPU(urlPlano, lista[0][0])
            return lista[0], extent, fc, polygonComuna
        else:
            mensaje("** Advertencia en obtieneInfoPara_PlanoUbicacion")
    except:
        mensaje("** Error en obtieneInfoPara_PlanoUbicacion")
    return None, None, None

def obtieneExtentComunaPlanoUbicacion(urlPlano, poligono):
    try:
        polygonBuffer = poligono.buffer(-10)
        polygonBufferNew = arcpy.Polygon(polygonBuffer.getPart(0), poligono.spatialReference)

        url = "{}/query".format(urlPlano)
        params = {
            'token': token,
            'f':'json',
            'where':'1=1',
            'returnExtentOnly':'true',
            'geometry':polygonBufferNew.JSON,
            'geometryType':'esriGeometryPolygon'
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        req = urllib2.Request(url, urllib.urlencode(params).encode('UTF-8'), headers)
        response = urllib2.urlopen(req).read()
        response_text = response.decode('UTF-8')
        j = json.loads(response_text)

        if j.has_key('extent'):
            je = j['extent']
            extent = arcpy.Extent(je['xmin'], je['ymin'], je['xmax'], je['ymax'])
            return extent
    except Exception:
        arcpy.AddMessage(sys.exc_info()[1].args[0])
    return None

# Funcion que obtiene el poligono de la Comuna para Plano de Ubicacion
def obtiene_PoligonoComunaPU(urlPlano, poligono):
    try:
        polygonBuffer = poligono.buffer(-10)
        polygonBufferNew = arcpy.Polygon(polygonBuffer.getPart(0), poligono.spatialReference)

        url = "{}/query".format(urlPlano)
        params = {
            'token': token,
            'f':'json',
            'where':'1=1',
            'returnExtentOnly':'false',
            'geometry':polygonBufferNew.JSON,
            'geometryType':'esriGeometryPolygon'
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        req = urllib2.Request(url, urllib.urlencode(params).encode('UTF-8'), headers)
        response = urllib2.urlopen(req).read()
        response_text = response.decode('UTF-8')
        j = json.loads(response_text)
        polygon = arcpy.AsShape(j["geometry"], True)

        # Poligono de comuna
        return polygon
    except Exception:
        arcpy.AddMessage(sys.exc_info()[1].args[0])
    return None

def listaMXDsPlanoUbicacion(estrato, ancho):

    d = {"Manzana":0,"RAU":1,"Rural":2}
    lista = []
    for e in config['estratos']:
        if e['nombre'] == estrato:
            if ancho:
                lista = [m for m in config['estratos'][d[estrato]]['mxdsPlanoUbicacion'] if m['ancho'] > m['alto']]
            else:
                lista = [m for m in config['estratos'][d[estrato]]['mxdsPlanoUbicacion'] if m['ancho'] <= m['alto']]
    return lista

def buscaTemplatePlanoUbicacion(extent):
    try:
        ancho = extent.XMax - extent.XMin
        alto = extent.YMax - extent.YMin
        lista = listaMXDsPlanoUbicacion(parametroEstrato, (ancho > alto))
        for infoMxd in lista:
            escala = mejorEscalaMXDPlanoUbicacion(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                mensaje('Se selecciono layout para Plano Ubicacion.')
                return mxd, infoMxd, escala

        # si no se ajusta dentro de las escalas limites se usa el papel más grande sin limite de escala
        escala = mejorEscalaMXD(infoMxd, alto, ancho)
        if escala != None:
            rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
            mxd = arcpy.mapping.MapDocument(rutaMXD)
            mensaje('Se selecciono layout para Plano Ubicacion (Excede escala)')
            mensaje("infoMxd = {}".format(infoMxd))
            mensaje("escala = {}".format(escala))
            return mxd, infoMxd, escala
    except:
        pass
    mensaje('** Error: No se selecciono layout para Plano Ubicacion.')
    return None, None, None

def mejorEscalaMXDPlanoUbicacion(mxd, alto, ancho):
    # Plano Ubicación A0 1: 7.500
    escalas = [e for e in range(5, 76)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
    return None

def actualizaVinetaManzanas_PlanoUbicacion(mxd, entidad):

    try:
        nombre_region = nombreRegion(entidad[2])
        nombre_provincia = nombreProvincia(entidad[3])
        nombre_comuna = nombreComuna(entidad[4])
        nombre_urbano = nombreUrbano(entidad[5])

        for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
            if parametroEncuesta == "ENE":
                if elm.name == "Nombre_Muestra":
                    elm.text = parametroEncuesta
            else:
                if elm.name == "Nombre_Muestra":
                    elm.text = parametroEncuesta+" "+parametroMarco
            if elm.name == "Nombre_Region":
                elm.text = nombre_region
            if elm.name == "Nombre_Provincia":
                elm.text = nombre_provincia
            if elm.name == "Nombre_Comuna":
                elm.text = nombre_comuna
            if elm.name == "Nombre_Urbano":
                elm.text = nombre_urbano
        mensaje("Se actualizaron las viñetas para manzana Plano Ubicacion.")
    except:
        mensaje("No se pudo actualizar las viñetas para manzana Plano Ubicacion.")

def actualizaVinetaSeccionRAU_PlanoUbicacion(mxd,datosRAU):

    try:
        nombre_region = nombreRegion(datosRAU[2])
        nombre_provincia = nombreProvincia(datosRAU[3])
        nombre_comuna = nombreComuna(datosRAU[4])
        nombre_urbano = nombreUrbano(datosRAU[5])

        for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
            if parametroEncuesta == "ENE":
                if elm.name == "Nombre_Muestra":
                    elm.text = parametroEncuesta
            else:
                if elm.name == "Nombre_Muestra":
                    elm.text = parametroEncuesta+" "+parametroMarco
            if elm.name == "Nombre_Region":
                elm.text = nombre_region
            if elm.name == "Nombre_Provincia":
                elm.text = nombre_provincia
            if elm.name == "Nombre_Comuna":
                elm.text = nombre_comuna
            if elm.name == "Nombre_Urbano":
                elm.text = nombre_urbano
        mensaje("Se actualizaron las viñetas para RAU Plano Ubicacion.")
    except:
        mensaje("No se pudo actualizar las viñetas para RAU Plano Ubicacion.")

def actualizaVinetaSeccionRural_PlanoUbicacion(mxd,datosRural):

    try:
        nombre_region = nombreRegion(datosRural[2])
        nombre_provincia = nombreProvincia(datosRural[3])
        nombre_comuna = nombreComuna(datosRural[4])

        for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
            if parametroEncuesta == "ENE":
                if elm.name == "Nombre_Muestra":
                    elm.text = parametroEncuesta
            else:
                if elm.name == "Nombre_Muestra":
                    elm.text = parametroEncuesta+" "+parametroMarco
            if elm.name == "Nombre_Region":
                elm.text = nombre_region
            if elm.name == "Nombre_Provincia":
                elm.text = nombre_provincia
            if elm.name == "Nombre_Comuna":
                elm.text = nombre_comuna
        mensaje("Se actualizaron las viñetas para Rural Plano Ubicacion.")
    except:
        mensaje("No se pudo actualizar las viñetas para Rural Plano Ubicacion.")

def destacaListaPoligonos(mxd, fc):
    try:
        mensaje("Destacando entidades")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.AddField_management(fc, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        with arcpy.da.UpdateCursor(fc, ["TIPO"]) as cursor:
            for a in cursor:
                a[0] = 2
                cursor.updateRow(a)
        arcpy.MakeFeatureLayer_management(fc, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        if parametroEstrato == "Manzana":
            sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr1.lyr")
        else:
            sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr2.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        mensaje("Entidades Destacadas")
    except:
        mensaje("No se pudo destacar entidades")

def listaEtiquetasPlanoUbicacion(estrato):
    d = {"Manzana":0,"RAU":1,"Rural":2}
    lista = []
    for e in config['estratos']:
        if e['nombre'] == estrato:
            lista = [m for m in config['estratos'][d[estrato]]['capas_labels_plano_ubicacion']]
    return lista

def preparaMapaPlanoUbicacion(mxd, extent, escala, datosRural):
    nombreCapa = leeNombreCapa("Rural")
    # Aqui deberia limpiar el mapa con las etiquetas del json *************************************************************************
    poligono = limpiaMapaRural_PU(mxd, datosRural, nombreCapa)
    if poligono != None:
        lista_etiquetas = listaEtiquetas("Rural")
        mensaje("Inicio preparación de etiquetas Rural.")
        for capa in lista_etiquetas:
            cortaEtiqueta(mxd, capa, poligono)
        mensaje("Fin preparación de etiquetas.")
        return True
    mensaje("No se completó la preparación del mapa para sección Rural.")
    return False

def buscaTemplatePlanoUbicacion_Manzana(extent):
    try:
        ancho = extent.XMax - extent.XMin
        alto = extent.YMax - extent.YMin
        lista = listaMXDsPlanoUbicacion(parametroEstrato, (ancho > alto))
        for infoMxd in lista:
            escala = mejorEscalaMXDPlanoUbicacion_Manzana(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                mensaje('Se selecciono layout para Plano Ubicacion.')
                return mxd, infoMxd, escala
    except:
        pass
    mensaje('** Error: No se selecciono layout para Plano Ubicacion.')
    return None, None, None

def mejorEscalaMXDPlanoUbicacion_Manzana(mxd, alto, ancho):
    mensaje("escala rango 500 a 100.000")
    escalas = [e for e in range(5, 10000)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
    return None

def buscaTemplatePlanoUbicacion_RAU(extent):
    try:
        ancho = extent.XMax - extent.XMin
        alto = extent.YMax - extent.YMin
        lista = listaMXDsPlanoUbicacion(parametroEstrato, (ancho > alto))
        for infoMxd in lista:
            escala = mejorEscalaMXDPlanoUbicacion_RAU(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                mensaje('Se selecciono layout para Plano Ubicacion.')
                return mxd, infoMxd, escala
    except:
        pass
    mensaje('** Error: No se selecciono layout para Plano Ubicacion.')
    return None, None, None

def mejorEscalaMXDPlanoUbicacion_RAU(mxd, alto, ancho):
    mensaje("escala rango 3.000 a 100.000")
    escalas = [e for e in range(30, 10000)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
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
        mensaje("Error en preparación de etiquetas.")
    return False

# limpiaMapaRural_PU(mxd, poligonoPlano, nombreCapa)
def limpiaMapaRural_PU(mxd, datosRural, nombreCapa):
    try:
        mensaje("Limpieza de mapa 'Sección Rural' iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, nombreCapa, df)[0] #campo_comuna  , SHAPE COMUNA POLIGONO DE LA CAPA COMUNA 
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyr.dataSource, "COMUNA"), int(datosRural[10]))
        lyr.definitionQuery = sql_exp
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)

        # aqui deberia pasarle el poligono de la comuna del plano de ubicacion  -->>> esta variable poligonoPlano *********************************************************************************************
        seccionRural = datosRural[0]
        ext = seccionRural.projectAs(df.spatialReference)
        dist = calculaDistanciaBufferRural(ext.area)
        dist_buff = float(dist.replace(" Meters", ""))
        polgrande = ext.buffer(dist_buff * 100)
        polchico = ext.buffer(dist_buff)
        poli = polgrande.difference(polchico)
        cursor = arcpy.da.InsertCursor(tm_layer, ['SHAPE@', "TIPO"])
        cursor.insertRow([poli,0])
        del cursor
        del FC
        arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        df1 = arcpy.mapping.ListDataFrames(mxd)[1]
        lyr1 = arcpy.mapping.ListLayers(mxd, nombreCapa, df1)[0]
        lyr1.definitionQuery = sql_exp
        lyr2 = arcpy.mapping.ListLayers(mxd, "COMUNA_ADYACENTE", df)[0]
        sql_exp = """{0} <> '{1}'""".format(arcpy.AddFieldDelimiters(lyr2.dataSource, "COMUNA"), int(datosRural[4]))
        lyr2.definitionQuery = sql_exp
        mensaje("Limpieza de mapa correcta.")
        return polchico
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa 'Sección Rural'.")
    return None

# ********************************************************************************************************************************
# Llamada a funcion que obtiene informacion para plano de ubicacion
# infoMarco.urlComunas = "https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/3",
entidad, extent, fc, poligonoPlano = obtieneInfoParaPlanoUbicacion(infoMarco.urlSecciones_Rural, infoMarco.urlComunas, token)
mxd, infoMxd, escala = buscaTemplatePlanoUbicacion(extent)
respuesta = preparaMapaPlanoUbicacion(mxd, poligonoPlano)
mensaje(respuesta)
