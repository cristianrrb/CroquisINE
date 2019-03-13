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

from util import mensaje, zoom, calculaExtent, obtieneToken, comprime, normalizaPalabra, Registro
import templates
import planoUbicacion

def mensajeEstado(registro):
    homologacion = "I"
    if registro.homologacion == 'Homologada No Idéntica' or registro.homologacion == 'Homologada No Idénticas':
        homologacion = 'NI'

    # Mensajes para analisis
    if parametroSoloAnalisis == "si":
        if registro.estadoViviendas == "Correcto":
            s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estadoViviendas) # Correcto
            print(s)
            arcpy.AddMessage(s)
            mensaje("Analisis: viviendas correctas.")
        if registro.estadoViviendas == "Rechazado":
            s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estadoViviendas) #Rechazado
            print(s)
            arcpy.AddMessage(s)
            mensaje("Analisis: Se rechazó la manzana.")
        if registro.estadoViviendas == "":
            s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estado) #Manzana no existe
            print(s)
            arcpy.AddMessage(s)
            mensaje("Analisis: Manzana No Existe")
        return "Analisis"

    # Mensajes para plano ubicacion
    if parametroSoloPlanoUbicacion == "Si":
        s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.motivo)
        print(s)
        arcpy.AddMessage(s)

        if registro.motivo == "Croquis generado":
            mensaje("Plano Ubicación: Se genera el croquis correctamente.")
        if registro.motivo == "Croquis No generado":
            mensaje("Plano Ubicación: No se logró generar el croquis Plano Ubicación.")
        return "Plano Ubicacion"
    else:
        # Mensajes para Generar PDF
        if parametroEstrato == "Manzana":
            if registro.estadoViviendas == "Correcto":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estadoViviendas)
                print(s)
                arcpy.AddMessage(s)
                mensaje("Genera croquis: viviendas correctas.")
            if registro.estadoViviendas == "Rechazado":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estadoViviendas)
                print(s)
                arcpy.AddMessage(s)
                mensaje("Genera croquis: Se rechazo la manzana.")
            if registro.estadoViviendas == "":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estado)
                print(s)
                arcpy.AddMessage(s)
                mensaje("Genera croquis: Manzana No Existe")

        if parametroEstrato == "RAU" or parametroEstrato == "Rural":
            s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estado)
            print(s)
            arcpy.AddMessage(s)

            if registro.estado == "Correcto":
                mensaje("Genera croquis: Se genera el croquis para Secciones")
            if registro.estado == "Incorrecto":
                mensaje("Genera croquis: No se logró generar el croquis para seccion.")
            if registro.estado == "Seccion No Existe":
                mensaje("Genera croquis: No se logró generar el croquis para seccion.")
        return "Croquis"

def obtieneInfoManzana(codigo, token):
    try:
        url = '{}/query?token={}&where=MANZENT+%3D+{}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(infoMarco.urlManzanas, token, codigo))

        fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT','MANZ']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if  lista != None and len(lista) == 1:
            metrosBuffer = calculaDistanciaBufferManzana(lista[0][1])
            extent = calculaExtent(fs, metrosBuffer)
            mensaje('Datos de manzana obtenidos correctamente.')
            return lista[0], extent
        else:
            mensaje("** El registro de manzana no existe")

            return None, None
    except:
        mensaje("** Error en obtieneInfoManzana")
        return None, None

def obtieneInfoSeccionRAU(codigo, token):
    try:
        url = '{}/query?token={}&where=CU_SECCION+%3D+{}&text=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(infoMarco.urlSecciones_RAU, token, codigo))

        fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION','CU_SECCION']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if lista != None and len(lista) == 1:
            metrosBuffer = calculaDistanciaBufferRAU(lista[0][1])
            extent = calculaExtent(fs, metrosBuffer)
            mensaje('Datos de RAU obtenidos correctamente.')
            return lista[0], extent
        else:
            mensaje("Error: El registro RAU no existe")
            return None, None
    except:
        mensaje("** Error en obtieneInfoSeccionRAU")
        return None, None

def obtieneInfoSeccionRural(codigo, token):
    try:
        url = '{}/query?token={}&where=CU_SECCION+%3D+{}&text=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(infoMarco.urlSecciones_Rural, token, codigo))

        fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','CUT','COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if lista != None and len(lista) == 1:
            metrosBuffer = calculaDistanciaBufferRural(lista[0][1])
            extent = calculaExtent(fs, metrosBuffer)
            mensaje('Datos de Rural obtenidos correctamente.')
            return lista[0], extent
        else:
            mensaje("El registro no existe")
            return None, None
    except:
        mensaje("Error URL servicio_Rural")
        return None, None

def obtieneListaAreasDestacadas(codigoSeccion, token):
    try:
        lista = []
        url = '{}/query?token={}&where=CU_SECCION+%3D+{}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(infoMarco.urlAreaDestacada, token, codigoSeccion))

        fields = ['SHAPE@', 'SHAPE@AREA', 'NUMERO']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            cuenta = [r for r in rows]

        if len(cuenta) > 0:
            buffer = os.path.join('in_memory', 'buffer_{}'.format(str(uuid.uuid1()).replace("-","")))
            fcBuffer = arcpy.Buffer_analysis(fs, buffer, "15 Meters")
            with arcpy.da.SearchCursor(fcBuffer, fields) as rows:
                lista = [r for r in rows]
            arcpy.Delete_management(buffer)
        return lista
    except:
        mensaje("Error obtieneListaAreasDestacadas")
        return

def obtieneInfoManzanaCenso2017(codigo, token):
    try:
        url = '{}/query?token={}&where=MANZENT+%3D+{}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(infoMarco.urlManzanasCenso2017, token, codigo))

        fields = ['SHAPE@AREA','MANZENT']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if  lista != None and len(lista) == 1:
            mensaje('Datos de manzana Censo 2017 obtenidos correctamente.')
            return lista[0]
        else:
            mensaje("El registro de manzana Censo 2017 no existe")
            return None
    except:
        mensaje("** Error en obtieneInfoManzana")
        return None

def comparaManzanas(datosManzana, datosManzana2017, registro):
    try:
        manzana2016 = datosManzana[1]
        manzana2017 = datosManzana2017[0]
        mensaje(manzana2016)
        mensaje(manzana2017)
        if manzana2017 != None:
            #print("----------------- Calculo ------------------------")
            if manzana2016 > manzana2017:
                diferencia = manzana2016 -  manzana2017
                porc = diferencia/manzana2016
                #mensaje(diferencia)
            else:
                diferencia = manzana2017 - manzana2016
                porc = diferencia/manzana2017
                #mensaje(diferencia)

            porcentaje = int(round(porc*100,0))
            #mensaje(porcentaje)

            if porcentaje <= 5:
                estadoSuperficie = "OK"
                motivoSuperficie = "Diferencia en superficie es menor a 5 porciento"
                #mensaje("OK: Diferencia en superficie es menor a 5 porciento")
            elif porcentaje >= 6 and porcentaje <= 40:
                estadoSuperficie = "Alerta"
                motivoSuperficie = "Diferencia en superficie entre 6 y 40 porciento"
                #mensaje("Alerta: Diferencia en superficie entre 6 y 40 porciento")
            elif porcentaje > 40:
                estadoSuperficie = "Rechazada"
                motivoSuperficie = "Diferencia en superficie supera 40 porciento"
    except:
        estadoSuperficie = "No encontrada"
        motivoSuperficie = "Manzana no encontrada en Censo2017"
    return estadoSuperficie, motivoSuperficie

def listaEtiquetas(estrato):
    d = {"Manzana":0,"RAU":1,"Rural":2}
    lista = []
    for e in config['estratos']:
        if e['nombre'] == estrato:
            lista = [m for m in config['estratos'][d[estrato]]['capas_labels']]
    return lista

def leeNombreCapa(estrato):
    #d = {"Manzana":0,"RAU":1,"Rural":2}
    lista = ""
    for e in config['estratos']:
        if e['nombre'] == estrato:
            lista = e['nombre_capa']
    return lista

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
        return '50 Meters'
    if area <= 1000000:     # 932000 .. 1000000  # VALIDAR ESTE VALOR
        return '150 Meters'
    return '500 Meters'     # valor por defecto

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
        mensaje('** Error en áreas de exclución.')
    return ""

def limpiaMapaManzana(mxd, manzana,cod_manz):
    try:
        mensaje("Limpieza de mapa iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        ext = manzana.projectAs(df.spatialReference)
        dist = calculaDistanciaBufferManzana(ext.area)
        dist_buff = float(dist.replace(" Meters", ""))
        polgrande = ext.buffer(dist_buff * 40)
        polchico = ext.buffer(dist_buff)
        poli = polgrande.difference(polchico)
        cursor = arcpy.da.InsertCursor(tm_layer, ['SHAPE@', "TIPO"])
        cursor.insertRow([poli,0])
        cursor.insertRow([ext,1])
        url = infoMarco.urlManzanas
        manz_excluidas = areasExcluidas(ext, url)
        if manz_excluidas != None:
            for manz in manz_excluidas:
                cursor.insertRow([manz,2])
        del cursor
        del FC
        arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        limpiaEsquicio(mxd, leeNombreCapa("Manzana"), "manzent", cod_manz)
        mensaje("Limpieza de mapa correcta.")
        return polchico
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa.")
    return None

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

def limpiaMapaRAU(mxd, datosRAU, capa):

    try:
        mensaje("Limpieza de mapa iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, capa, df)[0]
        cod_RAU = int(datosRAU[10])
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyr.dataSource, "cu_seccion"), cod_RAU)
        mensaje(sql_exp)
        lyr.definitionQuery = sql_exp
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        manzana = datosRAU[0]
        ext = manzana.projectAs(df.spatialReference)
        dist = calculaDistanciaBufferRAU(ext.area)
        dist_buff = float(dist.replace(" Meters", ""))
        polgrande = ext.buffer(dist_buff * 100)
        polchico = ext.buffer(dist_buff)
        dibujaSeudoManzanas(mxd, "Eje_Vial", polchico)
        poli = polgrande.difference(polchico)
        cursor = arcpy.da.InsertCursor(tm_layer, ['SHAPE@', "TIPO"])
        cursor.insertRow([poli,0])
        url = infoMarco.urlSecciones_RAU
        manz_excluidas = areasExcluidas(ext, url)
        if manz_excluidas != None:
            for manz in manz_excluidas:
                cursor.insertRow([manz,2])
        del cursor
        del FC
        arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        limpiaEsquicio(mxd, leeNombreCapa("RAU"), "cu_seccion", cod_RAU)
        mensaje("Limpieza de mapa correcta.")
        return polchico
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa.")
    return None

def limpiaMapaRural(mxd, datosRural, nombreCapa):
    try:
        mensaje("Limpieza de mapa 'Sección Rural' iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, nombreCapa, df)[0]
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyr.dataSource, "CU_SECCION"), int(datosRural[10]))
        lyr.definitionQuery = sql_exp
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
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

def dibujaSeudoManzanas(mxd, elLyr, poly):
    try:
        #path_scratchGDB = arcpy.env.scratchGDB
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr_sal = os.path.join("in_memory", "ejes")
        #lyr_man = os.path.join("in_memory", "seudoman")
        lyr = arcpy.mapping.ListLayers(mxd, elLyr, df)[0]
        mensaje("Layer encontrado {}".format(lyr.name))
        arcpy.SelectLayerByLocation_management(lyr, "INTERSECT", poly, "", "NEW_SELECTION")
        arcpy.Clip_analysis(lyr, poly.buffer(10), lyr_sal)
        cuantos = int(arcpy.GetCount_management(lyr_sal).getOutput(0))
        if cuantos > 0:
            tm_path = os.path.join("in_memory", "seudo_lyr")
            tm_path_buff = os.path.join("in_memory", "seudo_buff_lyr")
            arcpy.Buffer_analysis(lyr_sal, tm_path_buff, "3 Meters", "FULL", "FLAT", "ALL")
            arcpy.MakeFeatureLayer_management(tm_path_buff, tm_path)
            tm_layer = arcpy.mapping.Layer(tm_path)
            lyr_seudo = r"C:\CROQUIS_ESRI\Scripts\seudo_lyr.lyr"
            arcpy.ApplySymbologyFromLayer_management(tm_layer, lyr_seudo)
            arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        else:
            mensaje("No hay registros de {}".format(elLyr))
        return True
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en preparación de etiquetas.")
    return False

def preparaMapaManzana(mxd, extent, escala, datosManzana):
    actualizaVinetaManzanas(mxd, datosManzana)
    if zoom(mxd, extent, escala):
        poligono = limpiaMapaManzana(mxd, datosManzana[0], int(datosManzana[10]))
        if poligono != None:
            lista_etiquetas = listaEtiquetas("Manzana")
            mensaje("Inicio preparación de etiquetas Manzana.")
            for capa in lista_etiquetas:
                cortaEtiqueta(mxd, capa, poligono)
            mensaje("Fin preparación de etiquetas.")
            return True
    mensaje("No se completó la preparación del mapa para manzana.")
    return False

def preparaMapaRAU(mxd, extent, escala, datosRAU):
    actualizaVinetaSeccionRAU(mxd, datosRAU)
    if zoom(mxd, extent, escala):
        nombreCapa = leeNombreCapa("RAU")
        poligono = limpiaMapaRAU(mxd, datosRAU, nombreCapa)
        if poligono != None:
            lista_etiquetas = listaEtiquetas("RAU")
            mensaje("Inicio preparación de etiquetas RAU.")
            for capa in lista_etiquetas:
                cortaEtiqueta(mxd, capa, poligono)
            mensaje("Fin preparación de etiquetas.")
            return True
    mensaje("No se completó la preparación del mapa para sección RAU.")
    return False

def preparaMapaRural(mxd, extent, escala, datosRural):
    actualizaVinetaSeccionRural(mxd, datosRural)
    if zoom(mxd, extent, escala):
        nombreCapa = leeNombreCapa("Rural")
        poligono = limpiaMapaRural(mxd, datosRural, nombreCapa)
        if poligono != None:
            lista_etiquetas = listaEtiquetas("Rural")
            mensaje("Inicio preparación de etiquetas Rural.")
            for capa in lista_etiquetas:
                cortaEtiqueta(mxd, capa, poligono)
            mensaje("Fin preparación de etiquetas.")
            return True
    mensaje("No se completó la preparación del mapa para sección Rural.")
    return False

def validaRangoViviendas(viviendasEncuestar, totalViviendas, registro):
    if totalViviendas < 8:    # se descarta desde el principio
        registro.estadoViviendas = "Rechazado"
        registro.motivoViviendas = "Manzana con menos de 8 viviendas"
        mensaje("Manzana con menos de 8 viviendas. ({})".format(totalViviendas))
        return "Rechazado"

    if viviendasEncuestar == -1:    # no se evalua
        mensaje("No se evalua cantidad de viviendas a encuestar.")
        registro.estadoViviendas = "Correcto"
        registro.motivoViviendas = "Se cumple con el rango de viviendas de la manzana"
        return "Correcto"
    else:
        if dictRangos.has_key(viviendasEncuestar):
            rango = dictRangos[viviendasEncuestar]
            if rango[0] <= totalViviendas <= rango[1]:
                mensaje("Viviendas a Encuestar. ({})".format(viviendasEncuestar))
                mensaje("Rango Mínimo/Máximo. ({},{})".format(rango[0],rango[1]))
                mensaje("Total Viviendas. ({})".format(totalViviendas))
                mensaje("Se cumple con el rango de viviendas de la manzana.")
                registro.estadoViviendas = "Correcto"
                registro.motivoViviendas = "Se cumple con el rango de viviendas de la manzana"
                return "Correcto"
            else:
                mensaje("Viviendas a Encuestar. ({})".format(viviendasEncuestar))
                mensaje("Rango Mínimo/Máximo. ({},{})".format(rango[0],rango[1]))
                mensaje("Total Viviendas. ({})".format(totalViviendas))
                mensaje("No se cumple con el rango de viviendas de la manzana. ({} => [{},{}])".format(totalViviendas, rango[0], rango[1]))

                registro.estadoViviendas = "Rechazado"
                registro.motivoViviendas = "No se cumple con el rango de viviendas de la manzana"
                return "Rechazado"
        else:    # no existe el rango
            mensaje("No esta definido el rango para evaluacion de cantidad de viviendas a encuestar. ({})".format(viviendasEncuestar))

def procesaManzana(codigo, viviendasEncuestar):
    try:
        ############################################################## [INICIO SECCION ANALISIS DE MANZANA] #####################################################################
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            registro.homologacion, totalViviendas = obtieneHomologacion(codigo, infoMarco.urlHomologacion, token)
            resultado = validaRangoViviendas(viviendasEncuestar, totalViviendas, registro)

            datosManzana, extent = obtieneInfoManzana(codigo, token)
            datosManzana2017 = obtieneInfoManzanaCenso2017(codigo, token)
            est, mot = comparaManzanas(datosManzana, datosManzana2017, registro)
            registro.estadoSuperficie = est
            registro.motivoSuperficie = mot

            if datosManzana != None:
                registro.intersectaPE = intersectaConArea(datosManzana[0], infoMarco.urlPE, token)
                registro.intersectaAV = intersectaConArea(datosManzana[0], infoMarco.urlAV, token)
                registro.intersectaCRF = intersectaConArea(datosManzana[0], infoMarco.urlCRF, token)
                ############################################################## [FIN SECCION ANALISIS DE MANZANA] #####################################################################

                if not (registro.estadoViviendas == "Rechazado" or parametroSoloAnalisis == 'si'):
                    mxd, infoMxd, escala = controlTemplates.buscaTemplateManzana(extent)
                    if mxd != None:
                        mensaje(datosManzana)
                        if preparaMapaManzana(mxd, extent, escala, datosManzana):
                            mensaje("Registrando la operación.")
                            registro.formato = infoMxd['formato']
                            registro.orientacion = infoMxd['orientacion']
                            registro.escala = escala
                            registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosManzana)

                            nombrePDF = generaNombrePDF(datosManzana, infoMxd)
                            registro.rutaPDF = generaPDF(mxd, nombrePDF, datosManzana)

                            if registro.rutaPDF != "":
                                registro.estado = "Genera PDF"
                                registro.motivo = "Croquis generado"
                            else:
                                registro.estado = "Genera PDF"
                                registro.motivo = "Croquis No generado"

                # ************************** inicio if para solo para analisis cuando se Rechaza la manzana *********************************
                elif parametroSoloAnalisis == "si":
                    registro.estado = "Analiza"
                    registro.motivo = "Croquis No generado"
                # ************************** fin if para solo para analisis cuando se Rechaza la manzana ************************************
                # ************************** inicio if para Genera PDF pero Rechaza la manzana **********************************************
                else:
                    registro.estado = "Genera PDF"
                    registro.motivo = "Croquis No generado"
                # ************************** inicio if para Genera PDF pero Rechaza la manzana **********************************************

            else:
                mensaje("Manzana No Existe")
                registro.estado = "Manzana No Existe"
                registro.motivo = "Croquis No generado"
                registro.estadoViviendas = ""
                registro.motivoViviendas = ""
                registro.intersectaPE = ""
                registro.intersectaCRF = ""
                registro.intersectaAV = ""
                registro.Homologacion = ""
    except:
        registro.estado = "Manzana No Existe"
        registro.motivo = "Croquis No generado"
        registro.estadoViviendas = ""
        registro.motivoViviendas = ""
        registro.intersectaPE = ""
        registro.intersectaCRF = ""
        registro.intersectaAV = ""
        registro.Homologacion = ""
        mensaje("No se completó el proceso de Manzana.")
    mensajeEstado(registro)
    registros.append(registro)
    return

def procesaRAU(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            datosRAU, extent = obtieneInfoSeccionRAU(codigo, token)
            if datosRAU != None:
                mxd, infoMxd, escala = controlTemplates.buscaTemplateRAU(extent)
                if mxd != None:
                    if preparaMapaRAU(mxd, extent, escala, datosRAU):
                        mensaje("Registrando la operación.")
                        registro.formato = infoMxd['formato']
                        registro.orientacion = infoMxd['orientacion']
                        registro.escala = escala
                        registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosRAU)

                        nombrePDF = generaNombrePDF(datosRAU, infoMxd)
                        registro.rutaPDF = generaPDF(mxd, nombrePDF, datosRAU)

                        procesaAreasDestacadas(codigo, datosRAU, token)

                        if registro.rutaPDF != "":
                            registro.estado = "Correcto"
                            registro.motivo = "Croquis generado"
                        else:
                            registro.estado = "Incorrecto"
                            registro.motivo = "Croquis No generado"
            else:
                registro.estado = "Seccion No Existe"
                registro.motivo = "Croquis No generado"
    except:
        registro.estado = "Seccion No Existe"
        registro.motivo = "Croquis No generado"
        mensaje("No se completó el proceso de sección RAU.")
    registros.append(registro)
    mensajeEstado(registro)

    return

def procesaRural(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        datosRural, extent = obtieneInfoSeccionRural(codigo, token)
        if datosRural != None:
            mxd, infoMxd, escala = controlTemplates.buscaTemplateRural(extent)
            if mxd != None:
                if preparaMapaRural(mxd, extent, escala, datosRural):
                    mensaje("Registrando la operación.")
                    registro.formato = infoMxd['formato']
                    registro.orientacion = infoMxd['orientacion']
                    registro.escala = escala
                    registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosRural)

                    nombrePDF = generaNombrePDF(datosRural, infoMxd)
                    registro.rutaPDF = generaPDF(mxd, nombrePDF, datosRural)

                    procesaAreasDestacadas(codigo, datosRural, token)

                    if registro.rutaPDF != "":
                        registro.estado = "Correcto"
                        registro.motivo = "Croquis generado"
                    else:
                        registro.estado = "Incorrecto"
                        registro.motivo = "Croquis No generado"
        else:
            registro.estado = "Seccion No Existe"
            registro.motivo = "Croquis No generado"
    except:
        registro.estado = "No generado"
        registro.motivo = "Seccion no existe"
        mensaje("No se completó el proceso de sección Rural.")
    registros.append(registro)
    mensajeEstado(registro)
    return

def procesaAreasDestacadas(codigoSeccion, datosSeccion, token):
    mensaje("Validando areas destacadas.")
    listaAreas = obtieneListaAreasDestacadas(codigoSeccion, token)
    if len(listaAreas) > 0:
        mensaje("Se detectaron áreas destacadas dentro de la sección.")
        for area in listaAreas:
            procesaAreaDestacada(codigoSeccion, area, datosSeccion)
    else:
        mensaje("No se detectaron áreas destacadas dentro de la sección.")

def procesaAreaDestacada(codigoSeccion, area, datosSeccion):
    try:
        registro = Registro(codigoSeccion)
        extent = area[0].extent
        nroAnexo = area[2]
        mxd, infoMxd, escala = buscaTemplateAreaDestacada(extent)
        if mxd != None:
            if preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
                mensaje("Registrando la operación.")
                registro.formato = infoMxd['formato']
                registro.orientacion = infoMxd['orientacion']
                registro.escala = escala
                registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosSeccion)

                nombrePDF = generaNombrePDFAreaDestacada(parametroEstrato, datosSeccion, nroAnexo, infoMxd, parametroEncuesta, parametroMarco)
                registro.rutaPDF = generaPDF(mxd, nombrePDF, datosSeccion)

                if registro.rutaPDF != "":
                    registro.estado = "Correcto"
                    registro.motivo= "Croquis generado"
                else:
                    registro.estado = "Incorrecto"
                    registro.motivo = "Croquis No generado"
    except:
        #pass
        registro.estado = "No generado"
        registro.motivo = "Area destacada no existe"
    registros.append(registro)
    mensajeEstado(registro)
    return

def preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
    actualizaVinetaAreaDestacada(mxd, datosSeccion)   # Se actualiza viñeta de MXD de manzana con datos RAU o Rural
    if zoom(mxd, extent, escala):
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, "Areas_Destacadas_Marco", df)[0]
        lyr.visible = False
        #zoomEsquicio(mxd, datosSeccion[0].extent)
        mensaje("Se completó la preparación del mapa para area destacada.")
        return True
    mensaje("No se completó la preparación del mapa para area destacada.")
    return False

def buscaTemplateAreaDestacada(extent):
    # Por el momento se usan los mismos que para Rural
    mxd, infoMxd, escala = controlTemplates.buscaTemplateRural(extent)
    return mxd, infoMxd, escala

def generaListaCodigos(texto):
    try:
        lista = texto.split(",")
        listaNumeros = [int(x) for x in lista]
        return listaNumeros
    except:
        return []

def leeJsonConfiguracion():
    response = urllib.urlopen(urlConfiguracion)
    data = json.loads(response.read())
    return data

def actualizaVinetaManzanas(mxd,datosManzana):
    #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA']
    try:
        nombre_region = dic.nombreRegion(datosManzana[2])
        nombre_provincia = dic.nombreProvincia(datosManzana[3])
        nombre_comuna = dic.nombreComuna(datosManzana[4])
        nombre_urbano = nombreUrbano(datosManzana[5])
        codigo_barra = generaCodigoBarra(parametroEstrato,datosManzana)
        mensaje(codigo_barra)

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
            if elm.name == "CUT":
                elm.text = datosManzana[6]
            if elm.name == "COD_DISTRI":
                elm.text = datosManzana[7]
            if elm.name == "COD_ZONA":
                elm.text = datosManzana[8]
            if elm.name == "COD_MANZAN":
                elm.text = datosManzana[9]
            if elm.name == "barcode":
                elm.text = codigo_barra
        mensaje("Se actualizaron las viñetas para manzana.")
    except:
        mensaje("No se pudo actualizar las viñetas para manzana.")

def actualizaVinetaSeccionRAU(mxd,datosRAU):
    #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION']
    try:
        nombre_region = dic.nombreRegion(datosRAU[2])
        nombre_provincia = dic.nombreProvincia(datosRAU[3])
        nombre_comuna = dic.nombreComuna(datosRAU[4])
        nombre_urbano = nombreUrbano(datosRAU[5])
        codigo_barra = generaCodigoBarra(parametroEstrato,datosRAU)
        mensaje(codigo_barra)

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
            if elm.name == "CUT":
                elm.text = datosRAU[6]
            if elm.name == "EST_GEOGRAFICO":
                elm.text = datosRAU[7]
            if elm.name == "COD_CARTO":
                elm.text = datosRAU[8]
            if elm.name == "COD_SECCION":
                elm.text = datosRAU[9]
            if elm.name == "barcode":
                elm.text = codigo_barra
        mensaje("Se actualizaron las viñetas para RAU.")
    except:
        mensaje("No se pudo actualizar las viñetas para RAU.")

def actualizaVinetaSeccionRural(mxd,datosRural):
    #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','CUT','COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO']
    try:
        nombre_region = dic.nombreRegion(datosRural[2])
        nombre_provincia = dic.nombreProvincia(datosRural[3])
        nombre_comuna = dic.nombreComuna(datosRural[4])
        codigo_barra = generaCodigoBarra(parametroEstrato,datosRural)

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
            if elm.name == "CUT":
                elm.text = datosRural[5]
            if elm.name == "COD_SECCION":
                elm.text = datosRural[6]
            if elm.name == "COD_DISTRI":
                elm.text = datosRural[7]
            if elm.name == "EST_GEOGRAFICO":
                elm.text = datosRural[8]
            if elm.name == "COD_CARTO":
                elm.text = datosRural[9]
            if elm.name == "barcode":
                elm.text = codigo_barra
        mensaje("Se actualizaron las viñetas para Rural.")
    except:
        mensaje("No se pudo actualizar las viñetas para Rural.")

def actualizaVinetaAreaDestacada(mxd,datosSeccion):
    #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','CUT','COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']
    try:
        nombre_region = dic.nombreRegion(datosSeccion[2])
        nombre_provincia = dic.nombreProvincia(datosSeccion[3])
        nombre_comuna = dic.nombreComuna(datosSeccion[4])
        codigo_barra = generaCodigoBarra(parametroEstrato,datosSeccion)

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
            if elm.name == "CUT":
                elm.text = datosSeccion[5]
            if elm.name == "COD_SECCION":
                elm.text = datosSeccion[6]
            if elm.name == "COD_DISTRI":
                elm.text = datosSeccion[7]
            if elm.name == "EST_GEOGRAFICO":
                elm.text = datosSeccion[8]
            if elm.name == "COD_CARTO":
                elm.text = datosSeccion[9]
            if elm.name == "barcode":
                elm.text = codigo_barra
        mensaje("Se actualizaron las viñetas para Área Destacada.")
    except:
        mensaje("No se pudo actualizar las viñetas para Área Destacada.")

def generaNombrePDF(datosEntidad, infoMxd):
    f = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
    if parametroEstrato == "Manzana":
        tipo = "MZ"
        nombre = "{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[6]), int(datosEntidad[11]), infoMxd['formato'], infoMxd['orientacion'], parametroEncuesta, parametroMarco[2:4])
    elif parametroEstrato == "RAU":
        tipo = "RAU"
        nombre = "{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[10]), int(datosEntidad[9]), infoMxd['formato'], infoMxd['orientacion'], parametroEncuesta, parametroMarco[2:4])
    elif parametroEstrato == "Rural":
        tipo = "S_RUR"
        nombre = "{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[10]), int(datosEntidad[6]), infoMxd['formato'], infoMxd['orientacion'], parametroEncuesta, parametroMarco[2:4])
    return nombre

def generaNombrePDFAreaDestacada(estrato, datosEntidad, nroAnexo, infoMxd, encuesta, marco):
    if estrato == "RAU":
        tipo = "RAU"
        nombre = "{}_{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[10]), int(datosEntidad[9]), "Anexo_"+str(nroAnexo), infoMxd['formato'], infoMxd['orientacion'], encuesta, marco[2:4])
    elif estrato == "Rural":
        tipo = "S_RUR"
        nombre = "{}_{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[10]), int(datosEntidad[6]), "Anexo_"+str(nroAnexo), infoMxd['formato'], infoMxd['orientacion'], encuesta, marco[2:4])
    return nombre

def generaCodigoBarra(estrato, datosEntidad):
    if estrato == "Manzana":
        tipo = "MZ"
        nombre = "*{}-{}-{}-{}-{}*".format(tipo, int(datosEntidad[6]), int(datosEntidad[11]), parametroEncuesta, parametroMarco[2:4])
    elif estrato == "RAU":
        tipo = "RAU"
        nombre = "*{}-{}-{}-{}-{}*".format(tipo, int(datosEntidad[10]), int(datosEntidad[9]), parametroEncuesta, parametroMarco[2:4])
    elif estrato == "Rural":
        tipo = "SRUR"
        nombre = "*{}-{}-{}-{}-{}*".format(tipo, int(datosEntidad[10]), int(datosEntidad[6]), parametroEncuesta, parametroMarco[2:4])
    return nombre

def intersectaConArea(poligono, urlServicio, token):
    try:
        queryURL = "{}/query".format(urlServicio)
        params = {'token':token, 'f':'json', 'where':'1=1', 'outFields':'*', 'returnIdsOnly':'true', 'geometry':poligono.JSON, 'geometryType':'esriGeometryPolygon'}
        req = urllib2.Request(queryURL, urllib.urlencode(params))
        response = urllib2.urlopen(req)
        ids = json.load(response)
        if ids['objectIds'] != None:
            return "Si"
    except:
        pass
    return "No"

def obtieneHomologacion(codigo, urlServicio, token):
    try:
        #campos = "{},{}".format(infoMarco.nombreCampoTipoHomologacion.decode('utf8'), infoMarco.nombreCampoTotalViviendas.decode('utf8'))
        campos = "*"
        queryURL = "{}/query".format(urlServicio)
        params = {
            'token':token,
            'f':'json',
            'where':'{}={}'.format(infoMarco.nombreCampoIdHomologacion, codigo),
            'outFields': campos
        }
        req = urllib2.Request(queryURL, urllib.urlencode(params))
        response = urllib2.urlopen(req)
        valores = json.load(response)
        atributos = valores['features'][0]['attributes']
        return atributos[infoMarco.nombreCampoTipoHomologacion] , atributos[infoMarco.nombreCampoTotalViviendas]
    except:
        pass
    return "", -1

def escribeCSV(registros, f):
    try:
        if parametroEstrato == "Manzana":
            if parametroSoloPlanoUbicacion == "Si":
                tipo = "PlanoUbicacion"
                contenidoCsv = 2
            else:
                tipo = "MZ"
                contenidoCsv = 1

        elif parametroEstrato == "RAU":
            if parametroSoloPlanoUbicacion == "Si":
                tipo = "PlanoUbicacion"
                contenidoCsv = 2
            else:
                tipo = "RAU"
                contenidoCsv = 2

        elif parametroEstrato == "Rural":
            if parametroSoloPlanoUbicacion == "Si":
                tipo = "PlanoUbicacion"
                contenidoCsv = 2
            else:
                tipo = "Rural"
                contenidoCsv = 2

        # formato Genera PDF REPORTE MANZANA
        if contenidoCsv == 1:
            nombre = 'Reporte_log_{}_{}_{}.csv'.format(tipo, parametroEncuesta, f)
            rutaCsv = os.path.join(config['rutabase'], "LOG", nombre)
            mensaje("Ruta CSV :{}".format(rutaCsv))
            with open(rutaCsv, "wb") as f:
                wr = csv.writer(f, delimiter=';')
                a = ['Hora', 'Codigo', 'Estado Proceso', 'Motivo Proceso', 'Estado Superficie','Motivo Superficie','Estado Viviendas','Motivo Viviendas','CUT', 'CODIGO DISTRITO', 'CODIGO LOCALIDAD O ZONA', 'CODIGO ENTIDAD', 'Ruta PDF', 'Intersecta PE', 'Intersecta CRF', 'Intersecta AV', 'Homologacion', 'Formato / Orientacion', 'Escala', "Codigo barra"]
                wr.writerow(a)
                for r in registros:
                    cut, dis, area, loc, ent = descomponeManzent(r.codigo)
                    a = [r.hora, r.codigo, r.estado, r.motivo, r.estadoSuperficie, r.motivoSuperficie, r.estadoViviendas, r.motivoViviendas, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, r.homologacion.encode('utf8'), r.formato +" / "+ r.orientacion, r.escala, r.codigoBarra.encode('utf8')]
                    wr.writerow(a)

        # formato Genera PDF REPORTE (RAU Y RURAL) y (PLANO UBICACION Manzana RAU y Rural)
        if contenidoCsv == 2:
            nombre = 'Reporte_log_{}_{}_{}.csv'.format(tipo, parametroEncuesta, f)
            rutaCsv = os.path.join(config['rutabase'], "LOG", nombre)
            mensaje("Ruta CSV :{}".format(rutaCsv))
            with open(rutaCsv, "wb") as f:
                wr = csv.writer(f, delimiter=';')
                a = ['Hora', 'Codigo', 'Estado Proceso', 'Motivo Proceso','Ruta PDF','Formato / Orientacion', 'Escala', "Codigo barra"]
                wr.writerow(a)
                for r in registros:
                    a = [r.hora, r.codigo, r.estado, r.motivo, r.rutaPDF, r.formato +" / "+ r.orientacion, r.escala, r.codigoBarra.encode('utf8')]
                    wr.writerow(a)
        return rutaCsv
    except:
        return None

def nombreZip():
    if parametroEstrato == "Manzana":
        if parametroSoloPlanoUbicacion == "Si":
            tipo = "PlanoUbicacion"
        else:
            tipo = "MZ"
    elif parametroEstrato == "RAU":
        if parametroSoloPlanoUbicacion == "Si":
            tipo = "PlanoUbicacion"
        else:
            tipo = "RAU"
    elif parametroEstrato == "Rural":
        if parametroSoloPlanoUbicacion == "Si":
            tipo = "PlanoUbicacion"
        else:
            tipo = "Rural"

    nombre = 'Comprimido_{}_{}_{}.zip'.format(tipo, parametroEncuesta, f)
    return nombre

def descomponeManzent(codigo):
    c = "{}".format(codigo)
    cut = c[:-9]
    dis = c[-9:-7]
    area = c[-7:-6]
    loc = c[-6:-3]
    ent = c[-3:]
    return cut, dis, area, loc, ent

def enviarMail(registros):
    try:
        fromMail = "COMPLETAR"
        passwordFromMail = 'COMPLETAR'
        #fromMail = "sig@ine.cl"
        #passwordFromMail = "(ine2018)"
        toMail = "reinaldo.segura@ine.cl"

        nroReporte = f
        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')

        if parametroEncuesta == "ENE":
            msg['Subject'] = "Reporte Croquis INE Nro: "+str(nroReporte)+ " / Encuesta: "+parametroEncuesta+", Estrato: "+parametroEstrato
        else:
            msg['Subject'] = "Reporte Croquis INE Nro: "+str(nroReporte)+ " / Encuesta: "+parametroEncuesta+" "+parametroMarco+", Estrato: "+parametroEstrato
        msg['From'] = fromMail
        msg['To'] = toMail

        # Create the body of the message (a plain-text and an HTML version).
        html = """\
        <html>
        <head>
        <style>
        table, td, th {
          border: 1px solid #ddd;
          text-align: left;
        }
        table {
          border-collapse: collapse;
          width: 100%;
        }
        th, td {
          padding: 15px;
        }
        </style>
        </head>
        <body>
        <h2>Reporte Croquis INE Nro: """+str(nroReporte)+"""</h2>"""
        if parametroEncuesta == "ENE":
            html+= """<h3>Encuesta: """+str(parametroEncuesta)+""" / Estrato: """+str(parametroEstrato)+"""</h3>"""
        else:
            html+= """<h3>Encuesta: """+str(parametroEncuesta)+' '+str(parametroMarco)+""" / Estrato: """+str(parametroEstrato)+"""</h3>"""
        html+= """<p>Reporte croquis de alertas y rechazo para Instituto Nacional de Estadísticas de Chile</p>
        <u>Motivos de Rechazo:</u>
        <ul>
            <li type="disc">Rechazo, Manzana con menos de 8 viviendas; Cuando 'Estado' es, Rechazado.</li>
            <li type="disc">Rechazada, Diferencia de AreaManzana_2016 y AreaManzana_Censo2017 > 40%, Cuando 'Estado superficie' es, Rechazada</li>
        </ul>
        <u>Motivos de Alerta:</u>
        <ul>
            <li type="disc">Alerta, Diferencia de AreaManzana_2016 y AreaManzana_Censo2017 se encuentra entre 6% y 40% inclusive, Cuando 'Estado superficie' es, Alerta</li>
            <li type="disc">Alerta, Manzana Intersecta con Permiso de Edificación (PE); Cuando 'Intersecta PE' es, Si.</li>
            <li type="disc">Alerta, Manzana Intersecta con Certificado de Recepción Final (CRF); Cuando 'Intersecta CRF' es, Si.</li>
            <li type="disc">Alerta, Manzana Intersecta con Áreas Verdes (AV); Cuando 'Intersecta AV' es, Si.</li>
            <li type="disc">Alerta, Manzana Homologación No es Idéntica; cuando 'Homologación' es, Homologada No Idéntica(s)</li>
        </ul>
        <div style="overflow-x:auto;">
          <table>
              <tr>
                <th>#</th>
                <th>Hora</th>
                <th>Código</th>
                <th>Estado</th>
                <th>Motivo</th>
                <th>Estado Superficie</th>
                <th>Motivo Superficie</th>
                <th>Estado Viviendas</th>
                <th>Motivo Viviendas</th>
                <th>CUT</th>
                <th>C.DISTRITO</th>
                <th>C.ZONA</th>
                <th>C.ENTIDAD</th>
                <th>Ruta PDF</th>
                <th>Intersecta PE</th>
                <th>Intersecta CRF</th>
                <th>Intersecta AV</th>
                <th>Homologación</th>
                <th>Formato / Orientación</th>
                <th>Escala</th>
                <th>Código barra<th/>
              </tr>
            """
        for i, r in enumerate(registros, 1):
            if r.estadoViviendas == "Rechazado" or r.estadoSuperficie == "Alerta" or r.estadoSuperficie == "Rechazada" or r.intersectaPE == "Si" or r.intersectaCRF == "Si" or r.intersectaAV == "Si" or r.homologacion == 'Homologada No Idéntica' or r.homologacion == 'Homologada No Idénticas':
                cut, dis, area, loc, ent = descomponeManzent(r.codigo)
                a = [r.hora, r.codigo, r.estado, r.motivo, r.estadoSuperficie, r.motivoSuperficie, r.estadoViviendas, r.motivoViviendas, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, r.homologacion.encode('utf8'), r.formato +" / "+ r.orientacion, r.escala, r.codigoBarra.encode('utf8')]
                html +="""<tr>"""
                html += """<th>%s</th>""" % str(i)
                html += """<td>%s</td>""" % str(a[0]) #hora
                html += """<td>%s</td>""" % str(a[1]) #codigo
                html += """<td>%s</td>""" % str(a[2]) #estado
                html += """<td>%s</td>""" % str(a[3]) #motivo
                html += """<td>%s</td>""" % str(a[4]) #estadoSup
                html += """<td>%s</td>""" % str(a[5]) #motivoSup
                html += """<td>%s</td>""" % str(a[6]) #estadoViv
                html += """<td>%s</td>""" % str(a[7]) #motivoViv
                html += """<td>%s</td>""" % str(a[8]) #cut
                html += """<td>%s</td>""" % str(a[9]) #dis
                html += """<td>%s</td>""" % str(a[10]) #loc
                html += """<td>%s</td>""" % str(a[11]) #ent
                html += """<td>%s</td>""" % str(a[12]) #rutapdf
                html += """<td>%s</td>""" % str(a[13]) #intersectaPE
                html += """<td>%s</td>""" % str(a[14]) #intersectaCRF
                html += """<td>%s</td>""" % str(a[15]) #intersectaAV
                html += """<td>%s</td>""" % str(a[16]) #Homologacion
                html += """<td>%s</td>""" % str(a[17]) #formato orientacion
                html += """<td>%s</td>""" % str(a[18]) #escala
                html += """<td>%s</td>""" % str(a[19]) #codigoBarra
                html += """</tr>"""
        html+="""</table>
        </div>
        </br>
        <p><b>Departamento de Geografía</b></p>
        <p>Instituto Nacional de Estadísticas</p>
        <p>Fono: 232461860</p>
        </body>
        </html>
        """
        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        mailserver = smtplib.SMTP('smtp.office365.com',587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.login(fromMail, passwordFromMail)
        mailserver.sendmail(fromMail, toMail, msg.as_string())
        mensaje("Reporte Enviado")
        mailserver.quit()
    except:
        mensaje("No se pudo enviar correo electronico de Alertas y Rechazo, Verificar cuentas de correo")

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
        self.nombreCampoTipoHomologacion = "TIPO_HOMOLOGACIÓN"
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

class Parametros:
    def __init__(self):
        self.Encuesta = arcpy.GetParameterAsText(0)
        self.Marco = arcpy.GetParameterAsText(1)
        self.Estrato = arcpy.GetParameterAsText(2)   # Manzana RAU Rural
        self.Codigos = arcpy.GetParameterAsText(3)
        self.Viviendas = arcpy.GetParameterAsText(4)
        self.SoloAnalisis = arcpy.GetParameterAsText(5)
        self.SoloPlanoUbicacion = arcpy.GetParameterAsText(6)

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

arcpy.env.overwriteOutput = True

urlPortal = 'https://gis.ine.cl/portal'
usuario = 'esri_chile'
clave = '(esrichile2018)'

urlConfiguracion = 'https://gis.ine.cl/croquis/configuracion.json'
config = leeJsonConfiguracion()

dictRegiones = {r['codigo']:r['nombre'] for r in config['regiones']}
dictProvincias = {r['codigo']:r['nombre'] for r in config['provincias']}
dictComunas = {r['codigo']:r['nombre'] for r in config['comunas']}

dictRangos = {r[0]:[r[1],r[2]] for r in config['rangos']}   # para manzanas
#dictCamposId = {"Manzana": "MANZENT", "RAU": "CU_SECCION", "Rural": "CU_SECCION"}

# ---------------------- PARAMETROS DINAMICOS -------------------------
parametroEncuesta = arcpy.GetParameterAsText(0)
parametroMarco = arcpy.GetParameterAsText(1)
parametroEstrato = arcpy.GetParameterAsText(2)   # Manzana RAU Rural
parametroCodigos = arcpy.GetParameterAsText(3)
parametroViviendas = arcpy.GetParameterAsText(4)
parametroSoloAnalisis = arcpy.GetParameterAsText(5)
parametroSoloPlanoUbicacion = arcpy.GetParameterAsText(6)
# ---------------------- PARAMETROS DINAMICOS -------------------------
# ---------------------- PARAMETROS EN DURO ---------------------------
"""
parametroCodigos = "13126011003005,13126091002035,13126091003024"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "Manzana"
parametroViviendas = ""
parametroSoloAnalisis = ""
parametroSoloPlanoUbicacion = "Si"
"""
# --------------------------------------------------------------------
"""
parametroCodigos = "3202200055"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "RAU"
parametroViviendas = ""
parametroSoloAnalisis = ""
parametroSoloPlanoUbicacion = ""
"""
# --------------------------------------------------------------------
"""
parametroCodigos = "2203900013"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "Rural"
parametroViviendas = ""
parametroSoloAnalisis = ""
parametroSoloPlanoUbicacion = "Si"
"""
# ---------------------- PARAMETROS EN DURO ---------------------------

parametros = Parametros()
dic = Diccionario(config)
infoMarco = InfoMarco(parametroMarco, config)

controlTemplates = templates.Templates(config)

listaCodigos = generaListaCodigos(parametroCodigos)
listaViviendasEncuestar = generaListaCodigos(parametroViviendas)
registros = []

mensaje("Estrato: {}".format(parametroEstrato))

# ##################################################################### [INICIO DE EJECUCIÓN DEL PROCESO] #############################################################################

# SECCION GENERAR PLANO UBICACIÓN
if parametros.SoloPlanoUbicacion == 'Si':
    token = obtieneToken(usuario, clave, urlPortal)
    if token != None:
        plano = planoUbicacion.PlanoUbicacion(parametros, config, infoMarco, listaCodigos, controlTemplates, dic, token)
        registro = plano.procesa()
        registros.append(registro)
        mensajeEstado(registro)
# SECCION GENERAR CROQUIS
else:
    if parametroEstrato == "Manzana":
        dic.dictUrbano = {r['codigo']:r['nombre'] for r in config['urbanosManzana']}
    elif parametroEstrato == "RAU":
        dic.dictUrbano = {r['codigo']:r['nombre'] for r in config['urbanosRAU']}

    for indice, codigo in enumerate(listaCodigos):
        if parametroEstrato == 'Manzana':
            viviendas = -1
            if len(listaViviendasEncuestar) > 0:
                viviendas = listaViviendasEncuestar[indice]
            procesaManzana(codigo, viviendas)
        elif parametroEstrato == 'RAU':
            procesaRAU(codigo)
        elif parametroEstrato == 'Rural':
            procesaRural(codigo)
        else:
            mensaje("El estrato no existe")
            quit()
        mensaje("-------------------------------------------------\n")
# ######################################################################### [FIN DE EJECUCIÓN DEL PROCESO] #############################################################################


f = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
rutaCSV = escribeCSV(registros,f)

rutaZip = comprime(nombreZip(), registros, rutaCSV)
arcpy.SetParameterAsText(7, rutaZip)

mensaje("El GeoProceso ha terminado correctamente")
enviarMail(registros)

