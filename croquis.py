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

import util
from util import *
import templates
import planoUbicacion
import controladorManzanas

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

# para rau y rural
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
        mensaje("Limpieza de mapa 'Seccion Rural' iniciada.")
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

def preparaMapaRAU(mxd, extent, escala, datosRAU):
    actualizaVinetaSeccionRAU(mxd, datosRAU)
    if zoom(mxd, extent, escala):
        nombreCapa = leeNombreCapa("RAU")
        poligono = limpiaMapaRAU(mxd, datosRAU, nombreCapa)
        if poligono != None:
            lista_etiquetas = listaEtiquetas("RAU")
            mensaje("Inicio preparacion de etiquetas RAU.")
            for capa in lista_etiquetas:
                cortaEtiqueta(mxd, capa, poligono)
            mensaje("Fin preparacion de etiquetas.")
            return True
    mensaje("No se completo la preparacion del mapa para seccion RAU.")
    return False

def preparaMapaRural(mxd, extent, escala, datosRural):
    actualizaVinetaSeccionRural(mxd, datosRural)
    if zoom(mxd, extent, escala):
        nombreCapa = leeNombreCapa("Rural")
        poligono = limpiaMapaRural(mxd, datosRural, nombreCapa)
        if poligono != None:
            lista_etiquetas = listaEtiquetas("Rural")
            mensaje("Inicio preparacion de etiquetas Rural.")
            for capa in lista_etiquetas:
                cortaEtiqueta(mxd, capa, poligono)
            mensaje("Fin preparacion de etiquetas.")
            return True
    mensaje("No se completo la preparacion del mapa para seccion Rural.")
    return False

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
                        mensaje("Registrando la operacion.")
                        registro.formato = infoMxd['formato']
                        registro.orientacion = infoMxd['orientacion']
                        registro.escala = escala
                        registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosRAU)

                        nombrePDF = generaNombrePDF(datosRAU, infoMxd)
                        mensaje(nombrePDF)
                        rutaPDF = controlPDF.generaRutaPDF(nombrePDF, datosRAU)
                        mensaje(rutaPDF)
                        registro.rutaPDF = controlPDF.generaPDF(mxd, rutaPDF)

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
        registro.estado = "Error procesaRAU"
        registro.motivo = "Croquis No generado"
        mensaje("No se completo el proceso de seccion RAU.")
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
                    mensaje("Registrando la operacion.")
                    registro.formato = infoMxd['formato']
                    registro.orientacion = infoMxd['orientacion']
                    registro.escala = escala
                    registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosRural)

                    nombrePDF = generaNombrePDF(datosRural, infoMxd)
                    mensaje(nombrePDF)
                    rutaPDF = controlPDF.generaRutaPDF(nombrePDF, datosRural)
                    mensaje(rutaPDF)
                    registro.rutaPDF = controlPDF.generaPDF(mxd, rutaPDF)

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
        registro.estado = "Error procesaRural"
        registro.motivo = "Croquis No generado"
        mensaje("No se completo el proceso de seccion Rural.")
    registros.append(registro)
    mensajeEstado(registro)
    return

def procesaAreasDestacadas(codigoSeccion, datosSeccion, token):
    mensaje("Validando areas destacadas.")
    listaAreas = obtieneListaAreasDestacadas(codigoSeccion, token)
    if len(listaAreas) > 0:
        mensaje("Se detectaron areas destacadas dentro de la seccion.")
        for area in listaAreas:
            procesaAreaDestacada(codigoSeccion, area, datosSeccion)
    else:
        mensaje("No se detectaron areas destacadas dentro de la seccion.")

def procesaAreaDestacada(codigoSeccion, area, datosSeccion):
    try:
        registro = Registro(codigoSeccion)
        extent = area[0].extent
        nroAnexo = area[2]
        mxd, infoMxd, escala = buscaTemplateAreaDestacada(extent)
        if mxd != None:
            if preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
                mensaje("Registrando la operacion.")
                registro.formato = infoMxd['formato']
                registro.orientacion = infoMxd['orientacion']
                registro.escala = escala
                registro.codigoBarra = generaCodigoBarra(parametroEstrato,datosSeccion)

                nombrePDF = generaNombrePDFAreaDestacada(parametroEstrato, datosSeccion, nroAnexo, infoMxd, parametroEncuesta, parametroMarco)
                rutaPDF = controlPDF.generaRutaPDF(nombrePDF, datosSeccion)
                registro.rutaPDF = controlPDF.generaPDF(mxd, rutaPDF)

                if registro.rutaPDF != "":
                    registro.estado = "Correcto"
                    registro.motivo= "Croquis generado"
                else:
                    registro.estado = "Incorrecto"
                    registro.motivo = "Croquis No generado"
        else:
            registro.estado = "Incorrecto"
            registro.motivo = "Area destacada no existe"
    except:
        #pass
        registro.estado = "Error procesaAreaDestacada"
        registro.motivo = "Area destacada No generada"
    registros.append(registro)
    mensajeEstado(registro)
    return

def preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
    actualizaVinetaAreaDestacada(mxd, datosSeccion)   # Se actualiza vióeta de MXD de manzana con datos RAU o Rural
    if zoom(mxd, extent, escala):
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, "Areas_Destacadas_Marco", df)[0]
        lyr.visible = False
        zoomEsquicio(mxd, datosSeccion[0].extent)
        mensaje("Se completo la preparacion del mapa para area destacada.")
        return True
    mensaje("No se completo la preparacion del mapa para area destacada.")
    return False

def buscaTemplateAreaDestacada(extent):
    # Por el momento se usan los mismos que para Rural
    mxd, infoMxd, escala = controlTemplates.buscaTemplateAnexo(extent)
    return mxd, infoMxd, escala

def leeJsonConfiguracion():
    response = urllib.urlopen(urlConfiguracion)
    data = json.loads(response.read())
    return data

def actualizaVinetaSeccionRAU(mxd,datosRAU):
    #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION']
    try:
        nombre_region = dic.nombreRegion(datosRAU[2])
        nombre_provincia = dic.nombreProvincia(datosRAU[3])
        nombre_comuna = dic.nombreComuna(datosRAU[4])
        nombre_urbano = dic.nombreUrbano(datosRAU[5])
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
        mensaje("Se actualizaron las vinetas para RAU.")
    except:
        mensaje("No se pudo actualizar las vinetas para RAU.")

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
        mensaje("Se actualizaron las vinetas para Rural.")
    except:
        mensaje("No se pudo actualizar las vinetas para Rural.")

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
        mensaje("Se actualizaron las vinetas para area Destacada.")
    except:
        mensaje("No se pudo actualizar las vinetas para area Destacada.")

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
                a = ['Hora', 'Codigo', 'Estado Proceso', 'Motivo Proceso', 'Estado Superficie','Motivo Superficie','Area Manzana2016','Area Manzana2017','Estado Viviendas','Motivo Viviendas','CUT', 'CODIGO DISTRITO', 'CODIGO LOCALIDAD O ZONA', 'CODIGO ENTIDAD', 'Ruta PDF', 'Intersecta PE', 'Intersecta CRF', 'Intersecta AV', 'Homologacion', 'Formato / Orientacion', 'Escala', "Codigo barra"]
                wr.writerow(a)
                for r in registros:
                    cut, dis, area, loc, ent = descomponeManzent(r.codigo)
                    a = [r.hora, r.codigo, r.estado, r.motivo, r.estadoSuperficie, r.motivoSuperficie, r.area_manzana2016, r.area_manzana2017, r.estadoViviendas, r.motivoViviendas, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, r.homologacion.encode('utf8'), r.formato +" / "+ r.orientacion, r.escala, r.codigoBarra.encode('utf8')]
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

class Parametros:
    def __init__(self):
        self.Encuesta = arcpy.GetParameterAsText(0)
        self.Marco = arcpy.GetParameterAsText(1)
        self.Estrato = arcpy.GetParameterAsText(2)   # Manzana RAU Rural
        self.Codigos = arcpy.GetParameterAsText(3)
        self.Viviendas = arcpy.GetParameterAsText(4)
        self.SoloAnalisis = arcpy.GetParameterAsText(5)
        self.SoloPlanoUbicacion = arcpy.GetParameterAsText(6)

arcpy.env.overwriteOutput = True

urlPortal = 'https://gis.ine.cl/portal'
usuario = 'esri_chile'
clave = '(esrichile2018)'

urlConfiguracion = 'https://gis.ine.cl/croquis/configuracion_dev.json'
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
controlPDF = GeneraPDF(config, dic, parametros)

listaCodigos = generaListaCodigos(parametroCodigos)
listaViviendasEncuestar = generaListaCodigos(parametroViviendas)
registros = []

mensaje("Estrato: {}".format(parametroEstrato))

# ########################################################### [INICIO DE EJECUCIóN DEL PROCESO] #########################################################################

# SECCION GENERAR PLANO UBICACIóN
if parametros.SoloPlanoUbicacion == 'Si':
    token = obtieneToken(usuario, clave, urlPortal)
    if token != None:
        plano = planoUbicacion.PlanoUbicacion(parametros, config, infoMarco, listaCodigos, controlTemplates, dic, controlPDF, token)
        rutaZip = plano.procesa()

# SECCION GENERAR CROQUIS
else:
    if parametros.Estrato == "Manzana":
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            controlManzanas = controladorManzanas.ControladorManzanas(parametros, config, infoMarco, listaCodigos, controlTemplates, dic, controlPDF, token)
            rutaZip = controlManzanas.procesa()
    else:
        if parametros.Estrato == "RAU":
            dic.dictUrbano = {r['codigo']:r['nombre'] for r in config['urbanosRAU']}

        for indice, codigo in enumerate(listaCodigos):
            if parametros.Estrato == 'RAU':
                procesaRAU(codigo)
            elif parametros.Estrato == 'Rural':
                procesaRural(codigo)
            else:
                mensaje("El estrato no existe")
                quit()
            mensaje("-------------------------------------------------\n")

        f = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
        rutaCSV = escribeCSV(registros, f)
        rutaZip = comprime(nombreZip(), registros, rutaCSV)
# ########################################################### [FIN DE EJECUCIóN DEL PROCESO] #############################################################################

arcpy.SetParameterAsText(7, rutaZip)

mensaje("El GeoProceso ha terminado correctamente")
