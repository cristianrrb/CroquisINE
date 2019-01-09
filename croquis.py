# -*- coding: iso-8859-1 -*-

import arcpy
import os, urllib, urllib2, json, sys
import datetime
import csv
import uuid
import zipfile
import shutil
from arcpy import env

def mensaje(m):
    n = datetime.datetime.now()
    s = "[{}]: {}".format(n.strftime("%H:%M:%S"), m)
    print(s)
    arcpy.AddMessage(s)

def mensajeEstado(codigo, intersecta, estado):
    s = "#{}#:{},{}".format(codigo, intersecta, estado)
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

def obtieneInfoManzana(codigo, token):
    try:
        url = '{}/query?token={}&where=MANZENT+%3D+{}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(urlManzanas, token, codigo))

        fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if  lista != None and len(lista) == 1:
            metrosBuffer = calculaDistanciaBufferManzana(lista[0][1])
            extent = calculaExtent(fs, metrosBuffer)
            mensaje('Datos de manzana obtenidos correctamente.')
            return lista[0], extent
        else:
            mensaje("** Error: El registro de manzana no existe")
            return None, None
    except:
        mensaje("** Error en obtieneInfoManzana")
        return None, None

def obtieneInfoSeccionRAU(codigo, token):
    try:
        url = '{}/query?token={}&where=CU_SECCION+%3D+{}&text=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(urlSecciones_RAU, token, codigo))

        fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION','CU_SECCION']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if lista != None and len(lista) == 1:
            metrosBuffer = calculaDistanciaBufferRAU(lista[0][1])
            extent = calculaExtent(fs, metrosBuffer)
            return lista[0], extent
        else:
            mensaje("Error: El registro RAU no existe")
            return None, None
    except:
        mensaje("Error URL servicio_RAU")
        return None, None

def obtieneInfoSeccionRural(codigo, token):
    try:
        url = '{}/query?token={}&where=CU_SECCION+%3D+{}&text=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(urlSecciones_Rural, token, codigo))

        fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','CUT','COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']

        with arcpy.da.SearchCursor(fs, fields) as rows:
            lista = [r for r in rows]

        if lista != None and len(lista) == 1:
            metrosBuffer = calculaDistanciaBufferRural(lista[0][1])
            extent = calculaExtent(fs, metrosBuffer)
            return lista[0], extent
        else:
            mensaje("Error: El registro no existe")
            return None, None
    except:
        mensaje("Error URL servicio_Rural")
        return None

def listaMXDs(estrato, ancho):

    d = {"Manzana":0,"RAU":1,"Rural":2}

    lista = []
    for e in config['estratos']:
        if e['nombre'] == estrato:
            if ancho:
                lista = [m for m in config['estratos'][d[estrato]]['mxds'] if m['ancho'] > m['alto']]
            else:
                lista = [m for m in config['estratos'][d[estrato]]['mxds'] if m['ancho'] <= m['alto']]
    return lista

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

def calculaExtent(fs, metrosBuffer):
    try:
        buffer = os.path.join('in_memory', 'buffer_{}'.format(str(uuid.uuid1()).replace("-","")))
        fcBuffer = arcpy.Buffer_analysis(fs, buffer, metrosBuffer)
        with arcpy.da.SearchCursor(fcBuffer, ['SHAPE@']) as rows:
            lista = [r[0] for r in rows]

        arcpy.Delete_management(buffer)

        if lista != None and len(lista) > 0:
            mensaje('Extension del poligono obtenida correctamente.')
            return lista[0].extent
        else:
            mensaje("No se pudo calcular extension del poligono.")
            return None
    except:
        mensaje("** Error en calculaExtent.")
        return None

def mejorEscalaMXDManzana(mxd, alto, ancho):
    escalas = [e for e in range(5, 36)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
    return None

def mejorEscalaMXDRAU(mxd, alto, ancho):
    escalas = [e for e in range(5, 76)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
    return None

def mejorEscalaMXDRural(mxd, alto, ancho):
    escalas = [e for e in range(5, 201)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
    return None

def mejorEscalaMXD(mxd, alto, ancho):
    escalas = [e for e in range(5, 1000)]
    for e in escalas:
        if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
            return e * 100
    return None

def buscaTemplateManzana(extent):
    try:
        ancho = extent.XMax - extent.XMin
        alto = extent.YMax - extent.YMin
        lista = listaMXDs("Manzana", (ancho > alto))
        for infoMxd in lista:
            escala = mejorEscalaMXDManzana(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                mensaje('Se selecciono layout para manzana.')
                return mxd, infoMxd, escala
    except:
        pass
    mensaje('** Error: No se selecciono layout para manzana.')
    return None, None, None

def buscaTemplateRAU(extent):
    try:
        ancho = extent.XMax - extent.XMin
        alto = extent.YMax - extent.YMin
        lista = listaMXDs("RAU", (ancho > alto))
        for infoMxd in lista:
            escala = mejorEscalaMXDRAU(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                mensaje('Se selecciono layout para RAU.')
                return mxd, infoMxd, escala

        # si no se ajusta dentro de las escalas limites se usa el papel más grande sin limite de escala
        escala = mejorEscalaMXD(infoMxd, alto, ancho)
        if escala != None:
            rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
            mxd = arcpy.mapping.MapDocument(rutaMXD)
            mensaje('Se selecciono layout para RAU.')
            return mxd, infoMxd, escala
    except:
        pass
    mensaje('** Error: No se selecciono layout para RAU. (Excede escala)')
    return None, None, None

def buscaTemplateRural(extent):
    try:
        ancho = extent.XMax - extent.XMin
        alto = extent.YMax - extent.YMin
        lista = listaMXDs("Rural", (ancho > alto))
        for infoMxd in lista:
            escala = mejorEscalaMXDRural(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                mensaje('Se selecciono layout para Rural.')
                return mxd, infoMxd, escala

        # si no se ajusta dentro de las escalas limites se usa el papel más grande sin limite de escala
        escala = mejorEscalaMXD(infoMxd, alto, ancho)
        if escala != None:
            rutaMXD = os.path.join(config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
            mxd = arcpy.mapping.MapDocument(rutaMXD)
            mensaje('Se selecciono layout para Rural. (Excede escala)')
            return mxd, infoMxd, escala
    except:
        pass
    mensaje('** Error: No se selecciono layout para Rural.')
    return None, None, None

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

def limpiaMapaManzana(mxd, manzana):
    try:
        mensaje("Limpieza de mapa 'Manzana' iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        mensaje("Proyectando")
        ext = manzana.projectAs(df.spatialReference)
        mensaje("Proyectado")
        polgrande = ext.buffer(200)
        polchico = ext.buffer(15)
        poli = polgrande.difference(polchico)
        cursor = arcpy.da.InsertCursor(tm_layer, ['SHAPE@', "TIPO"])
        cursor.insertRow([poli,0])
        cursor.insertRow([ext,1])
        del cursor
        del FC
        arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        mensaje("Limpieza de mapa correcta.")
        return polchico
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa 'Manzana'.")
    return None

def limpiaMapaEsquicio(mxd, nombreEstrato):
    try:
        mensaje("Limpieza de esquicio iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[1]
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        mensaje("Proyectando")
        ext = nombreEstrato.projectAs(df.spatialReference)
        mensaje("Proyectado")
        cursor = arcpy.da.InsertCursor(tm_layer, ['SHAPE@', "TIPO"])
        cursor.insertRow([ext,2])
        del cursor
        del FC
        arcpy.mapping.AddLayer(df, tm_layer, "TOP")
        mensaje("Limpieza de esquicio correcta.")
        return True
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa.")
    return None

def limpiaMapaRAU(mxd, datosRAU, nombreCapa):
    try:
        mensaje("Limpieza de mapa 'Sección RAU' iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, nombreCapa, df)[0]
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyr.dataSource, "CU_SECCION"), int(datosRAU[10]))
        lyr.definitionQuery = sql_exp
        lyr1 = arcpy.mapping.ListLayers(mxd, "Mz_Rau", df)[0]
        lyr1.definitionQuery = sql_exp
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        seccionRau = datosRAU[0]
        mensaje("Proyectando")
        ext = seccionRau.projectAs(df.spatialReference)
        mensaje("Proyectado")
        dist = calculaDistanciaBufferRAU(ext.area)
        dist_buff = float(dist.replace(" Meters", ""))
        polgrande = ext.buffer(dist_buff * 20)
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
        mensaje("Limpieza de mapa correcta.")
        return polchico
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa 'Sección RAU'.")
    return None

def limpiaMapaRural(mxd, datosRural, nombreCapa):
    try:
        mensaje("Limpieza de mapa 'Sección Rural' iniciada.")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr = arcpy.mapping.ListLayers(mxd, nombreCapa, df)[0]
        mensaje("Limpieza de mapa iniciada.")
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyr.dataSource, "CU_SECCION"), int(datosRural[10]))
        mensaje(sql_exp)
        lyr.definitionQuery = sql_exp
        FC = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(FC, "tipo", "LONG")
        tm_path = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(FC, tm_path)
        tm_layer = arcpy.mapping.Layer(tm_path)
        sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
        seccionRural = datosRural[0]
        mensaje("Proyectando")
        ext = seccionRural.projectAs(df.spatialReference)
        mensaje("Proyectado")
        dist = calculaDistanciaBufferRAU(ext.area)
        dist_buff = float(dist.replace(" Meters", ""))
        polgrande = ext.buffer(dist_buff * 20)
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
        mensaje("Limpieza de mapa correcta.")
        return polchico
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("Error en limpieza de mapa 'Sección Rural'.")
    return None

def cortaEtiqueta(mxd, elLyr, poly):
    try:
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr_sal = os.path.join("in_memory", elLyr)
        lyr = arcpy.mapping.ListLayers(mxd, elLyr, df)[0]
        mensaje("Layer encontrado {}".format(lyr.name))
        arcpy.Clip_analysis(lyr, poly, lyr_sal)
        cuantos = arcpy.GetCount_management(lyr_sal)
        if cuantos > 0:
            arcpy.CopyFeatures_management(lyr_sal, arcpy.env.scratchGDB + "/" + elLyr)
            lyr.replaceDataSource(arcpy.env.scratchGDB, 'FILEGDB_WORKSPACE', elLyr , True)
            mensaje("Etiquetas correcta de {}".format(elLyr))
        else:
            mensaje("No hay registros de {}".format(elLyr))
        return True
    except Exception:
        mensaje(sys.exc_info()[1].args[0])
        mensaje("No se encontró etiqueta.")
    return False

def preparaMapaManzana(mxd, extent, escala, datosManzana):
    actualizaVinetaManzanas(mxd, datosManzana)
    if zoom(mxd, extent, escala):
        poligono = limpiaMapaManzana(mxd, datosManzana[0])
        if limpiaMapaEsquicio(mxd, datosManzana[0]):
            if poligono != None:
                lista_etiquetas = listaEtiquetas(parametroEstrato)
                mensaje("Inicio preparación de etiquetas Manzana.")
                for capa in lista_etiquetas:
                    cortaEtiqueta(mxd, capa, poligono)
                mensaje("Fin preparación de etiquetas.")
                return True
    mensaje("No se completo la preparación del mapa para manzana.")
    return False

def preparaMapaRAU(mxd, extent, escala, datosRAU):
    actualizaVinetaSeccionRAU(mxd, datosRAU)
    if zoom(mxd, extent, escala):
        nombreCapa = leeNombreCapa(parametroEstrato)
        poligono = limpiaMapaRAU(mxd, datosRAU, nombreCapa)
        if limpiaMapaEsquicio(mxd, datosRAU[0]):
            if poligono != None:
                lista_etiquetas = listaEtiquetas(parametroEstrato)
                mensaje("Inicio preparación de etiquetas RAU.")
                for capa in lista_etiquetas:
                    cortaEtiqueta(mxd, capa, poligono)
                mensaje("Fin preparación de etiquetas.")
                return True
    mensaje("No se completo la preparación del mapa para sección RAU.")
    return False

def preparaMapaRural(mxd, extent, escala, datosRural):
    actualizaVinetaSeccionRural(mxd, datosRural)
    if zoom(mxd, extent, escala):
        nombreCapa = leeNombreCapa(parametroEstrato)
        poligono = limpiaMapaRural(mxd, datosRural, nombreCapa)
        if limpiaMapaEsquicio(mxd, datosRural[0]):
            if poligono != None:
                lista_etiquetas = listaEtiquetas(parametroEstrato)
                mensaje("Inicio preparación de etiquetas Rural.")
                for capa in lista_etiquetas:
                    cortaEtiqueta(mxd, capa, poligono)
                mensaje("Fin preparación de etiquetas.")
                return True
    mensaje("No se completo la preparación del mapa para sección Rural.")
    return False

def procesaManzana(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            datosManzana, extent = obtieneInfoManzana(codigo, token)
            if datosManzana != None:
                registro.intersecta = intersectaAreaRechazo(datosManzana[0])
                mxd, infoMxd, escala = buscaTemplateManzana(extent)
                if mxd != None:
                    if preparaMapaManzana(mxd, extent, escala, datosManzana):
                        mensaje("Registrando la operación.")
                        registro.formato = infoMxd['formato']
                        registro.orientacion = infoMxd['orientacion']
                        registro.escala = escala

                        nombrePDF = generaNombrePDF(parametroEstrato, codigo, infoMxd, parametroEncuesta, parametroMarco)
                        registro.rutaPDF = generaPDF(mxd, nombrePDF, datosManzana)
                        registros.append(registro)

                        if registro.rutaPDF == "":
                            mensajeEstado(codigo, registro.intersecta, "No Existe")
                        else:
                            mensajeEstado(codigo, registro.intersecta, "Correcto")

                        mensaje("Se procesó la manzana correctamente.")
    except:
        #mensaje("** Error: procesaManzana.")
        mensaje("No se completó el proceso de manzana.")

def procesaRAU(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            datosRAU, extent = obtieneInfoSeccionRAU(codigo, token)
            if datosRAU != None:
                registro.intersecta = intersectaAreaRechazo(datosRAU[0])
                mxd, infoMxd, escala = buscaTemplateRAU(extent)
                if mxd != None:
                    if preparaMapaRAU(mxd, extent, escala, datosRAU):
                        mensaje("Registrando la operación.")
                        registro.formato = infoMxd['formato']
                        registro.orientacion = infoMxd['orientacion']
                        registro.escala = escala

                        nombrePDF = generaNombrePDF(parametroEstrato, codigo, infoMxd, parametroEncuesta, parametroMarco)
                        registro.rutaPDF = generaPDF(mxd, nombrePDF, datosRAU)
                        registros.append(registro)

                        if registro.rutaPDF == "":
                            mensajeEstado(codigo, registro.intersecta, "No Existe")
                        else:
                            mensajeEstado(codigo, registro.intersecta, "Correcto")

                        procesaAreasDestacadas(codigo, datosRAU, token)

                        mensaje("Se procesó la sección RAU correctamente.")
    except:
        #mensaje("** Error: procesaRAU.")
        mensaje("No se completó el proceso de sección RAU.")

def procesaRural(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        datosRural, extent = obtieneInfoSeccionRural(codigo, token)
        if datosRural != None:
            registro.intersecta = intersectaAreaRechazo(datosRural[0])
            mxd, infoMxd, escala = buscaTemplateRural(extent)
            if mxd != None:
                if preparaMapaRural(mxd, extent, escala, datosRural):
                    mensaje("Registrando la operación.")
                    registro.formato = infoMxd['formato']
                    registro.orientacion = infoMxd['orientacion']
                    registro.escala = escala

                    nombrePDF = generaNombrePDF(parametroEstrato, codigo, infoMxd, parametroEncuesta, parametroMarco)
                    registro.rutaPDF = generaPDF(mxd, nombrePDF, datosRural)
                    registros.append(registro)

                    if registro.rutaPDF == "":
                        mensajeEstado(codigo, registro.intersecta, "No Existe")
                    else:
                        mensajeEstado(codigo, registro.intersecta, "Correcto")

                    procesaAreasDestacadas(codigo, datosRural, token)

                    mensaje("Se procesó la sección Rural correctamente.")
    except:
        #mensaje("** Error: procesaRural.")
        mensaje("No se completó el proceso de sección Rural.")

def procesaAreasDestacadas(codigoSeccion, datosSeccion, token):
    mensaje("Validando areas destacadas.")
    listaAreas = obtieneListaAreasDestacadas(codigoSeccion, token)
    if len(listaAreas) > 0:
        mensaje("Se detectaron areas destacadas dentro de la sección.")
        for area in listaAreas:
            procesaAreaDestacada(codigoSeccion, area, datosSeccion)
    else:
        mensaje("No se detectaron areas destacadas dentro de la sección.")

def procesaAreaDestacada(codigoSeccion, area, datosSeccion):
    registro = Registro(codigoSeccion)
    extent = area[0].extent
    mxd, infoMxd, escala = buscaTemplateAreaDestacada(extent)
    if mxd != None:
        if preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
            mensaje("Registrando la operación.")
            registro.formato = infoMxd['formato']
            registro.orientacion = infoMxd['orientacion']
            registro.escala = escala
            codigo = "{}_{}".format(codigoSeccion, area[2])
            nombrePDF = generaNombrePDF(parametroEstrato, codigo, infoMxd, parametroEncuesta, parametroMarco)
            registro.rutaPDF = generaPDF(mxd, nombrePDF, datosSeccion)
            registros.append(registro)
            mensaje("Se procesó el área destacada correctamente.")

def preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
    actualizaVinetaManzanas(mxd, datosSeccion)   # Se actualiza viñeta de MXD de manzana con datos RAU o Rural
    if zoom(mxd, extent, escala):
        """ poligono = limpiaMapaManzana(mxd, datosSeccion[0])
        if limpiaMapaManzanaEsquicio(mxd, datosSeccion[0]):
            if poligono != None:
                lista_etiquetas = listaEtiquetas("Manzana")
                mensaje("Inicio preparación de etiquetas.")
                for capa in lista_etiquetas:
                    mensaje(capa)
                    cortaEtiqueta(mxd, capa, poligono)
                mensaje("Fin preparación de etiquetas.") """
        mensaje("Se completo la preparación del mapa para area destacada.")
        return True
    mensaje("No se completo la preparación del mapa para area destacada.")
    return False

def buscaTemplateAreaDestacada(extent):
    # Por el momento se usan los mismos que para Rural
    mxd, infoMxd, escala = buscaTemplateRural(extent)
    return mxd, infoMxd, escala

def obtieneListaAreasDestacadas(codigoSeccion, token):
    try:
        lista = []
        url = '{}/query?token={}&where=CU_SECCION+%3D+{}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson'
        fs = arcpy.FeatureSet()
        fs.load(url.format(urlAreaDestacada, token, codigoSeccion))

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
        return []

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
    try:
        #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA']
        for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
            if elm.name == "Nombre_Muestra":
                elm.text = parametroEncuesta+" "+parametroMarco
            if elm.name == "Nombre_Region":
                elm.text = datosManzana[2]
            if elm.name == "Nombre_Provincia":
                elm.text = datosManzana[3]
            if elm.name == "Nombre_Comuna":
                elm.text = datosManzana[4]
            if elm.name == "Nombre_Urbano":
                elm.text = datosManzana[5]
            if elm.name == "CUT":
                elm.text = datosManzana[6]
            if elm.name == "COD_DISTRI":
                elm.text = datosManzana[7]
            if elm.name == "COD_ZONA":
                elm.text = datosManzana[8]
            if elm.name == "COD_MANZAN":
                elm.text = datosManzana[9]
        mensaje("Se actualizaron las viñetas para manzana.")
    except:
        mensaje("No se pudo actualizar las viñetas para manzana.")

def actualizaVinetaSeccionRAU(mxd,datosRAU):
    try:
        #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION']
        codigo_barra = generaCodigoBarra(parametroEstrato,datosRAU)
        for elm in arcpy.mapping.ListLayoutElements(mxd,"TEXT_ELEMENT"):
            if elm.name == "Nombre_Muestra":
                elm.text = parametroEncuesta+" "+parametroMarco
            if elm.name == "Nombre_Region":
                elm.text = datosRAU[2]
            if elm.name == "Nombre_Provincia":
                elm.text = datosRAU[3]
            if elm.name == "Nombre_Comuna":
                elm.text = datosRAU[4]
            if elm.name == "Nombre_Urbano":
                elm.text = datosRAU[5]
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
    try:
        #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','CUT','COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO']
        codigo_barra = generaCodigoBarra(parametroEstrato,datosRural)
        for elm in arcpy.mapping.ListLayoutElements(mxd,"TEXT_ELEMENT"):
            if elm.name == "Nombre_Muestra":
                elm.text = parametroEncuesta+" "+parametroMarco
            if elm.name == "Nombre_Region":
                elm.text = datosRural[2]
            if elm.name == "Nombre_Provincia":
                elm.text = datosRural[3]
            if elm.name == "Nombre_Comuna":
                elm.text = datosRural[4]
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

def generaPDF(mxd, nombrePDF, datos):

    id_region = int(datos[2])
    id_comuna = int(datos[4])
    dict_region = {1:'TARAPACA',2:'ANTOFAGASTA',3:'ATACAMA',4:'COQUIMBO',5:'VALPARAISO',6:'OHIGGINS',7:'MAULE',8:'BIOBIO',9:'ARAUCANIA',10:'LOS_LAGOS',11:'AYSEN',12:'MAGALLANES',13:'METROPOLITANA',14:'LOS_RIOS',15:'ARICA_PARINACOTA',16:'NUBLE'}

    ruta = os.path.join(config['rutabase'],"MUESTRAS_PDF","ENE",dict_region[id_region], nombrePDF)
    mensaje(ruta)
    arcpy.mapping.ExportToPDF(mxd, ruta)
    mensaje("Exportado a pdf")
    return ruta

def generaNombrePDF(estrato, codigo, infoMxd, encuesta, marco):
    if estrato == "Manzana":
        tipo = "Mz"
    elif estrato == "RAU":
        tipo = "RAU"
    elif estrato == "Rural":
        tipo = "S_RUR"
    nombre = "{}_{}_{}_{}_{}_{}.pdf".format(tipo, codigo, infoMxd['formato'], infoMxd['orientacion'], encuesta, marco)
    return nombre

def generaCodigoBarra(estrato, datosEstrato):
    if estrato == "RAU":
        tipo = "RAU"
    elif estrato == "Rural":
        tipo = "S_RUR"
    nombre = "*{}-{}-{}-{}_{}*".format(tipo, datosEstrato[4], datosEstrato[10], parametroEncuesta, parametroMarco[2:4])
    return nombre

def intersectaAreaRechazo(poligono):
    try:
        d = {0:'Permiso edificacion', 1:'CRF'}
        poly = poligono.JSON
        params = {'f':'json', 'where':'1=1', 'outFields':'*', 'returnIdsOnly':'true', 'geometry':poly, 'geometryType':'esriGeometryPolygon'}
        for i in range(0,2):
            queryURL = "{}/{}/query".format(urlAreaRechazo, i)
            req = urllib2.Request(queryURL, urllib.urlencode(params))
            response = urllib2.urlopen(req)

            ids = json.load(response)
            if ids['objectIds'] != None:
                mensaje('Intersecta con areas.')
                return d[i]
    except:
        mensaje('** Error en intersecta.')
    mensaje('No intersecta con areas.')
    return ""

def escribeCSV(registros):
    try:
        f = "{}".format(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
        nombre = 'log_{}_{}.csv'.format(f, str(uuid.uuid1()).replace("-",""))
        rutaCsv = os.path.join(config['rutabase'], "LOG", nombre)
        mensaje("Ruta CSV :{}".format(rutaCsv))
        with open(rutaCsv, "wb") as f:
            wr = csv.writer(f, delimiter=';')
            for r in registros:
                a = [r.hora, r.codigo, r.rutaPDF, r.intersecta, r.formato, r.orientacion, r.escala]
                wr.writerow(a)
        return rutaCsv
    except:
        return None

def comprime(registros, rutaCSV):
    try:
        f = "{}".format(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
        nombre = 'exportacion_{}_{}.zip'.format(f, str(uuid.uuid1()).replace("-",""))
        rutaZip = os.path.join(arcpy.env.scratchFolder, nombre)
        mensaje("Ruta ZIP {}".format(rutaZip))
        listaPDFs = [r.rutaPDF for r in registros if r.rutaPDF != ""]
        with zipfile.ZipFile(rutaZip, 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(rutaCSV, os.path.basename(rutaCSV))
            for archivo in listaPDFs:
                mensaje("Comprimiendo {}".format(os.path.basename(archivo)))
                myzip.write(archivo, os.path.basename(archivo))
        return rutaZip
    except:
        return None

class Registro:
    def __init__(self, codigo):
        self.hora = "{}".format(datetime.datetime.now().strftime("%H:%M:%S"))
        self.codigo = codigo
        self.rutaPDF = ""
        self.intersecta = ""
        self.formato = ""
        self.orientacion = ""
        self.escala = ""

arcpy.env.overwriteOutput = True

# Nuevos Servicios
urlManzanas        = 'https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/1'
urlSecciones_RAU   = 'https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/2'
urlSecciones_Rural = 'https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/0'
urlAreaRechazo     = 'https://gis.ine.cl/public/rest/services/ESRI/areas_de_rechazo/MapServer'
urlAreaDestacada   = 'https://gis.ine.cl/public/rest/services/ESRI/areas_destacadas/MapServer/0'

urlConfiguracion   = 'https://gis.ine.cl/croquis/configuracion.json'
urlPortal          = 'https://gis.ine.cl/portal'
usuario = 'esri_chile'
clave = '(esrichile2018)'

config = leeJsonConfiguracion()

# ---------------------- PARAMETROS DINAMICOS -------------------------
parametroEncuesta = arcpy.GetParameterAsText(0)
parametroMarco = arcpy.GetParameterAsText(1)
parametroEstrato = arcpy.GetParameterAsText(2)   # Manzana RAU Rural
parametroCodigos = arcpy.GetParameterAsText(3)
# ---------------------- PARAMETROS DINAMICOS -------------------------

# ---------------------- PARAMETROS EN DURO ---------------------------
"""
# --------------------------------------------------------------------
parametroCodigos = "15101021001002"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "Manzana"
# --------------------------------------------------------------------
parametroCodigos = "2301200044"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "RAU"
# --------------------------------------------------------------------
parametroCodigos = "2203900013"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "Rural"
# --------------------------------------------------------------------
"""
# ---------------------- PARAMETROS EN DURO ---------------------------

listaCodigos = generaListaCodigos(parametroCodigos)
registros = []

mensaje("Estrato: {}".format(parametroEstrato))

for codigo in listaCodigos:
    if parametroEstrato == 'Manzana':
        procesaManzana(codigo)
    elif parametroEstrato == 'RAU':
        procesaRAU(codigo)
    elif parametroEstrato == 'Rural':
        procesaRural(codigo)
    else:
        mensaje("El estrato no existe")
        quit()
    mensaje("-------------------------------------------------\n")

rutaCSV = escribeCSV(registros)
rutaZip = comprime(registros, rutaCSV)
arcpy.SetParameterAsText(4, rutaZip)

mensaje("El GeoProceso ha terminado correctamente")

"""
for mxd in mxd_list:

    current_mxd = arcpy.mapping.MapDocument(os.path.join(ws,mxd))

    pdf_name = os.path.join(pdfws,mxd[:-4])+ ".pdf"

    pdfDoc = arcpy.mapping.PDFDocumentCreate(pdf_name)  # create the PDF document object

    for pageNum in range(1, current_mxd.dataDrivenPages.pageCount + 1):

        current_mxd.dataDrivenPages.currentPageID = pageNum

        page_pdf = os.path.join(pdfws,mxd[:-4])+ + str(pageNum) + ".pdf"

        arcpy.mapping.ExportToPDF(current_mxd, page_pdf)

        pdfDoc.appendPages(page_pdf) # add pages to it

        os.remove(page_pdf)  # delete the file



    pdfDoc.saveAndClose()  # save the pdf for the mxd
"""
