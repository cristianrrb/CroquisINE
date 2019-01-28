# -*- coding: iso-8859-1 -*-
import arcpy
import os, urllib, urllib2, json, sys
import datetime, csv, uuid, zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def mensaje(m):
    n = datetime.datetime.now()
    s = "[{}]: {}".format(n.strftime("%H:%M:%S"), m)
    print(s)
    arcpy.AddMessage(s)

def mensajeEstado(registro):
    homologacion = "I"
    if registro.homologacion == 'Homologada No Idéntica':
        homologacion = 'NI'

    s = "#{}#:{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estado)
    print(s)
    arcpy.AddMessage(s)

    if registro.estado == "Correcto":
        mensaje("Se genero el croquis correctamente.")
    if registro.estado == "No generado":
        mensaje("No se logro generar el croquis.")
    if registro.estado == "Rechazado":
        mensaje("Se rechazo la manzana.")

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
            mensaje("** Error: El registro de manzana no existe")
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
        fs.load(url.format(infoMarco.urlSecciones_Rural, token, codigo))

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
        return []

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
        path_scratchGDB = arcpy.env.scratchGDB
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyr_sal = os.path.join("in_memory", "ejes")
        lyr_man = os.path.join("in_memory", "seudoman")
        lyr = arcpy.mapping.ListLayers(mxd, elLyr, df)[0]
        mensaje("Layer encontrado {}".format(lyr.name))
        arcpy.SelectLayerByLocation_management(lyr, "INTERSECT", poly, "", "NEW_SELECTION")
        arcpy.Clip_analysis(lyr, poly.buffer(10), lyr_sal)
        cuantos = int(arcpy.GetCount_management(lyr_sal).getOutput(0))
        if cuantos > 0:
            tm_path = os.path.join("in_memory", "seudo_lyr")
            tm_path_buff = os.path.join("in_memory", "seudo_buff_lyr")
            arcpy.Buffer_analysis(lyr_sal, tm_path_buff, "2 Meters", "FULL", "FLAT", "ALL")
            arcpy.MakeFeatureLayer_management(tm_path_buff, tm_path)
            tm_layer = arcpy.mapping.Layer(tm_path)
            lyr_seudo = r"C:\CROQUIS_ESRI\Scripts\seudo_lyr.lyr"
            arcpy.ApplySymbologyFromLayer_management(tm_layer, lyr_seudo)
            arcpy.mapping.AddLayer(df, tm_layer, "TOP")
            #mensaje("aqui")
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
    mensaje("No se completo la preparación del mapa para manzana.")
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
    mensaje("No se completo la preparación del mapa para sección RAU.")
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
    mensaje("No se completo la preparación del mapa para sección Rural.")
    return False

def validaRangoViviendas(viviendasEncuestar, totalViviendas, registro):
    if totalViviendas < 8:    # se descarta desde el principio
        registro.estado = "Rechazado"
        registro.motivoRechazo = "Manzana con menos de 8 viviendas. ({})".format(totalViviendas)
        mensaje("Manzana con menos de 8 viviendas. ({})".format(totalViviendas))

    if viviendasEncuestar == -1:    # no se evalua
        mensaje("No se evalua cantidad de viviendas a encuestar.")
    else:
        if dictRangos.has_key(viviendasEncuestar):
            rango = dictRangos[viviendasEncuestar]
            if rango[0] <= totalViviendas <= rango[1]:
                mensaje("Viviendas a Encuestar. ({})".format(viviendasEncuestar))
                mensaje("Rango Mínimo/Máximo. ({},{})".format(rango[0],rango[1]))
                mensaje("Total Viviendas. ({})".format(totalViviendas))
                mensaje("Se cumple con el rango de viviendas de la manzana.")
            else:
                mensaje("Viviendas a Encuestar. ({})".format(viviendasEncuestar))
                mensaje("Rango Mínimo/Máximo. ({},{})".format(rango[0],rango[1]))
                mensaje("Total Viviendas. ({})".format(totalViviendas))
                mensaje("No se cumple con el rango de viviendas de la manzana. ({} => [{},{}])".format(totalViviendas, rango[0], rango[1]))

                registro.estado = "Rechazado"
                registro.motivoRechazo = "No se cumple con el rango de viviendas de la manzana. ({} => [{},{}])".format(totalViviendas, rango[0], rango[1])
        else:    # no existe el rango
            mensaje("No esta definido el rango para evaluacion de cantidad de viviendas a encuestar. ({})".format(viviendasEncuestar))

def procesaManzana(codigo, viviendasEncuestar):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            registro.homologacion, totalViviendas = obtieneHomologacion(codigo, infoMarco.urlHomologacion, token)
            validaRangoViviendas(viviendasEncuestar, totalViviendas, registro)

            if parametroSoloAnalisis == 'si':
                mensaje("** Solo se realiza analisis, no se generará el croquis.")
            else:
                if registro.estado != "Rechazado":
                    datosManzana, extent = obtieneInfoManzana(codigo, token)
                    if datosManzana != None:
                        registro.intersectaPE = intersectaConArea(datosManzana[0], infoMarco.urlPE, token)
                        registro.intersectaAV = intersectaConArea(datosManzana[0], infoMarco.urlAV, token)
                        registro.intersectaCRF = intersectaConArea(datosManzana[0], infoMarco.urlCRF, token)
                        mxd, infoMxd, escala = buscaTemplateManzana(extent)
                        if mxd != None:
                            if preparaMapaManzana(mxd, extent, escala, datosManzana):
                                #mensaje("Registrando la operación.")
                                registro.formato = infoMxd['formato']
                                registro.orientacion = infoMxd['orientacion']
                                registro.escala = escala

                                nombrePDF = generaNombrePDF(parametroEstrato, datosManzana, infoMxd, parametroEncuesta, parametroMarco)
                                registro.rutaPDF = generaPDF(mxd, nombrePDF, datosManzana)

                                if registro.rutaPDF != "":
                                    registro.estado = "Correcto"

        registros.append(registro)
        mensajeEstado(registro)
        return
    except:
        pass
    mensaje("No se completó el proceso de manzana.")

def procesaRAU(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        if token != None:
            datosRAU, extent = obtieneInfoSeccionRAU(codigo, token)
            if datosRAU != None:
                mxd, infoMxd, escala = buscaTemplateRAU(extent)
                if mxd != None:
                    if preparaMapaRAU(mxd, extent, escala, datosRAU):
                        mensaje("Registrando la operación.")
                        registro.formato = infoMxd['formato']
                        registro.orientacion = infoMxd['orientacion']
                        registro.escala = escala

                        nombrePDF = generaNombrePDF(parametroEstrato, datosRAU, infoMxd, parametroEncuesta, parametroMarco)
                        registro.rutaPDF = generaPDF(mxd, nombrePDF, datosRAU)

                        procesaAreasDestacadas(codigo, datosRAU, token)

                        if registro.rutaPDF != "":
                            registro.estado = "Correcto"

        registros.append(registro)
        mensajeEstado(registro)
        return
    except:
        pass
    mensaje("No se completó el proceso de sección RAU.")

def procesaRural(codigo):
    try:
        registro = Registro(codigo)
        token = obtieneToken(usuario, clave, urlPortal)
        datosRural, extent = obtieneInfoSeccionRural(codigo, token)
        if datosRural != None:
            mxd, infoMxd, escala = buscaTemplateRural(extent)
            if mxd != None:
                if preparaMapaRural(mxd, extent, escala, datosRural):
                    mensaje("Registrando la operación.")
                    registro.formato = infoMxd['formato']
                    registro.orientacion = infoMxd['orientacion']
                    registro.escala = escala

                    nombrePDF = generaNombrePDF(parametroEstrato, datosRural, infoMxd, parametroEncuesta, parametroMarco)
                    registro.rutaPDF = generaPDF(mxd, nombrePDF, datosRural)

                    procesaAreasDestacadas(codigo, datosRural, token)

                    if registro.rutaPDF != "":
                        registro.estado = "Correcto"

        registros.append(registro)
        mensajeEstado(registro)
        return
    except:
        pass
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
    nroAnexo = area[2]
    mxd, infoMxd, escala = buscaTemplateAreaDestacada(extent)
    if mxd != None:
        if preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
            mensaje("Registrando la operación.")
            registro.formato = infoMxd['formato']
            registro.orientacion = infoMxd['orientacion']
            registro.escala = escala
            nombrePDF = generaNombrePDFAreaDestacada(parametroEstrato, datosSeccion, nroAnexo, infoMxd, parametroEncuesta, parametroMarco)
            registro.rutaPDF = generaPDF(mxd, nombrePDF, datosSeccion)
            registros.append(registro)
            mensaje("Se procesó el área destacada correctamente.")

def preparaMapaAreaDestacada(mxd, extent, escala, datosSeccion):
    actualizaVinetaAreaDestacada(mxd, datosSeccion)   # Se actualiza viñeta de MXD de manzana con datos RAU o Rural
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
        nombre_region = nombreRegion(datosManzana[2])
        nombre_provincia = nombreProvincia(datosManzana[3])
        nombre_comuna = nombreComuna(datosManzana[4])
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
        nombre_region = nombreRegion(datosRAU[2])
        nombre_provincia = nombreProvincia(datosRAU[3])
        nombre_comuna = nombreComuna(datosRAU[4])
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
        nombre_region = nombreRegion(datosRural[2])
        nombre_provincia = nombreProvincia(datosRural[3])
        nombre_comuna = nombreComuna(datosRural[4])
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
        nombre_region = nombreRegion(datosSeccion[2])
        nombre_provincia = nombreProvincia(datosSeccion[3])
        nombre_comuna = nombreComuna(datosSeccion[4])
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

def generaPDF(mxd, nombrePDF, datos):

    nueva_region = normalizaPalabra(nombreRegion(datos[2]))
    nueva_comuna = normalizaPalabra(nombreComuna(datos[4]))

    if parametroEstrato == "Rural":
        rutaDestino = os.path.join(config['rutabase'], "MUESTRAS_PDF", parametroEncuesta, nueva_region, nueva_comuna)
    else:
        nueva_urbano = normalizaPalabra(nombreUrbano(datos[5]))
        rutaDestino = os.path.join(config['rutabase'], "MUESTRAS_PDF", parametroEncuesta, nueva_region, nueva_comuna, nueva_urbano)

    data_frame = 'PAGE_LAYOUT'
    df_export_width = 640 #not actually used when data_fram is set to 'PAGE_LAYOUT'
    df_export_height = 480 #not actually used when data_fram is set to 'PAGE_LAYOUT'
    resolution = 300
    image_quality = 'BEST' #'BEST' 'FASTER'
    color_space = 'RGB'
    compress_vectors = True
    image_compression = 'ADAPTIVE'
    picture_symbol = 'RASTERIZE_BITMAP'
    convert_markers = True
    embed_fonts = True

    if not os.path.exists(rutaDestino):
        os.makedirs(rutaDestino)

    destinoPDF = os.path.join(rutaDestino, nombrePDF)
    mensaje(destinoPDF)
    arcpy.mapping.ExportToPDF(mxd, destinoPDF, data_frame, df_export_width, df_export_height, resolution, image_quality, color_space, compress_vectors, image_compression, picture_symbol, convert_markers, embed_fonts)
    mensaje("Exportado a pdf")
    return destinoPDF

def generaNombrePDF(estrato, datosEntidad, infoMxd, encuesta, marco):
    if estrato == "Manzana":
        tipo = "MZ"
        nombre = "{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[6]), int(datosEntidad[11]), infoMxd['formato'], infoMxd['orientacion'], encuesta, marco[2:4])
    elif estrato == "RAU":
        tipo = "RAU"
        nombre = "{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[10]), int(datosEntidad[9]), infoMxd['formato'], infoMxd['orientacion'], encuesta, marco[2:4])
    elif estrato == "Rural":
        tipo = "S_RUR"
        nombre = "{}_{}_{}_{}_{}_{}_{}.pdf".format(tipo, int(datosEntidad[10]), int(datosEntidad[6]), infoMxd['formato'], infoMxd['orientacion'], encuesta, marco[2:4])
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
        nombre = "*{}-{}-{}-{}_{}*".format(tipo, int(datosEntidad[6]), int(datosEntidad[11]), parametroEncuesta, parametroMarco[2:4])
    elif estrato == "RAU":
        tipo = "RAU"
        nombre = "*{}-{}-{}-{}_{}*".format(tipo, int(datosEntidad[10]), int(datosEntidad[9]), parametroEncuesta, parametroMarco[2:4])
    elif estrato == "Rural":
        tipo = "S_RUR"
        nombre = "*{}-{}-{}-{}_{}*".format(tipo, int(datosEntidad[10]), int(datosEntidad[6]), parametroEncuesta, parametroMarco[2:4])
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
            tipo = "MZ"
        elif parametroEstrato == "RAU":
            tipo = "RAU"
        elif parametroEstrato == "Rural":
            tipo = "Rural"

        nombre = 'Reporte_{}_{}_{}.csv'.format(tipo, parametroEncuesta, f)
        rutaCsv = os.path.join(config['rutabase'], "LOG", nombre)
        mensaje("Ruta CSV :{}".format(rutaCsv))
        with open(rutaCsv, "wb") as f:
            wr = csv.writer(f, delimiter=';')
            a = ['Hora', 'Codigo', 'Estado', 'Motivo rechazo', 'CUT', 'CODIGO DISTRITO', 'CODIGO LOCALIDAD O ZONA', 'CODIGO ENTIDAD O MANZANA', 'Ruta PDF', 'Intersecta PE', 'Intersecta CRF', 'Intersecta AV', 'Homologacion', 'Formato', 'Orientacion', 'Escala']
            wr.writerow(a)
            for r in registros:
                if r.estado != "Correcto" or r.intersectaPE == "Si" or r.intersectaCRF == "Si" or r.intersectaAV == "Si" or r.homologacion == 'Homologada No Idéntica' or r.homologacion == 'Homologada No Idénticas':
                    cut, dis, area, loc, ent = descomponeManzent(r.codigo)
                    a = [r.hora, r.codigo, r.estado, r.motivoRechazo, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, r.homologacion.encode('utf8'), r.formato, r.orientacion, r.escala]
                    wr.writerow(a)
        return rutaCsv
    except:
        return None

def comprime(registros, rutaCSV, f):
    try:
        if parametroEstrato == "Manzana":
            tipo = "MZ"
        elif parametroEstrato == "RAU":
            tipo = "RAU"
        elif parametroEstrato == "Rural":
            tipo = "Rural"

        nombre = 'Comprimido_{}_{}_{}.zip'.format(tipo, parametroEncuesta, f)
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

def descomponeManzent(codigo):
    c = "{}".format(codigo)
    cut = c[:-9]
    dis = c[-9:-7]
    area = c[-7:-6]
    loc = c[-6:-3]
    ent = c[-3:]
    return cut, dis, area, loc, ent

def nombreRegion(codigo):
    if dictRegiones.has_key(codigo):
        return dictRegiones[codigo].encode('utf8')
    else:
        return codigo

def nombreProvincia(codigo):
    if dictProvincias.has_key(codigo):
        return dictProvincias[codigo].encode('utf8')
    else:
        return codigo

def nombreComuna(codigo):
    if dictComunas.has_key(codigo):
        return dictComunas[codigo].encode('utf8')
    else:
        return codigo

def nombreUrbano(codigo):
    if diccionario.has_key(codigo):
        return diccionario[codigo].encode('utf8')
    else:
        return codigo

def enviarMail(registros, f):

    fromMail = "mjimenez@esri.cl"
    passwordFromMail = 'Marce6550esRi'
    #fromMail = "sig@ine.cl"
    #passwordFromMail = "(ine2018)"
    toMail = "mjimenez@esri.cl"
    nroReporte = f

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Reporte Croquis INE Nro: "+str(f)+ " / Encuesta: "+parametroEncuesta+", Estrato: "+parametroEstrato
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
    <h2>Reporte Croquis INE Nro: """+str(f)+"""</h2>
    <h3>Encuesta: """+str(parametroEncuesta)+""" / Estrato: """+str(parametroEstrato)+"""</h3>
    <p>Reporte croquis de alertas y rechazo para Instituto Nacional de Estadísticas de Chile</p>
    <u>Motivos de Rechazo y/o Alertas:</u>
    <ul>
        <li type="disc">Rechazo, Manzana con menos de 8 viviendas; Cuando 'Motivo Rechazo' es, Rechazado.</li>
        <li type="disc">Alerta, Manzana Intersecta con Permiso de Edificación (PE); Cuando 'Intersecta PE' es, Si.</li>
        <li type="disc">Alerta, Manzana Intersecta con Certificado de Recepción Final (CRF); Cuando 'Intersecta CRF' es, Si.</li>
        <li type="disc">Alerta, Manzana Intersecta con Áreas Verdes (AV); Cuando 'Intersecta AV' es, Si.</li>
        <li type="disc">Alerta, Manzana Homologación No es Idéntica; cuando 'Homologación' es, Homologada No Idéntica</li>
    </ul>
    <div style="overflow-x:auto;">
      <table>
          <tr>
            <th>#</th>
            <th>Hora</th>
            <th>Código</th>
            <th>Estado</th>
            <th>Motivo Rechazo</th>
            <th>CUT</th>
            <th>C.DISTRITO</th>
            <th>C.ZONA</th>
            <th>C.ENTIDAD</th>
            <th>Ruta PDF</th>
            <th>Intersecta PE</th>
            <th>Intersecta CRF</th>
            <th>Intersecta AV</th>
            <th>Homologación</th>
            <th>Formato</th>
            <th>Orientación</th>
            <th>Escala</th>
          </tr>
        """

    for i, r in enumerate(registros,1):
        if r.estado != "Correcto" or r.intersectaPE == "Si" or r.intersectaCRF == "Si" or r.intersectaAV == "Si" or r.homologacion == 'Homologada No Idéntica' or r.homologacion == 'Homologada No Idénticas':
            cut, dis, area, loc, ent = descomponeManzent(r.codigo)
            a = [r.hora, r.codigo, r.estado, r.motivoRechazo, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, r.homologacion.encode('utf8'), r.formato, r.orientacion, r.escala]
            html +="""<tr>"""
            html += """<th>%s</th>""" % str(i)
            html += """<td>%s</td>""" % str(a[0])
            html += """<td>%s</td>""" % str(a[1])
            html += """<td>%s</td>""" % str(a[2])
            html += """<td>%s</td>""" % str(a[3])
            html += """<td>%s</td>""" % str(a[4])
            html += """<td>%s</td>""" % str(a[5])
            html += """<td>%s</td>""" % str(a[6])
            html += """<td>%s</td>""" % str(a[7])
            html += """<td>%s</td>""" % str(a[8])
            html += """<td>%s</td>""" % str(a[9])
            html += """<td>%s</td>""" % str(a[10])
            html += """<td>%s</td>""" % str(a[11])
            html += """<td>%s</td>""" % str(a[12])
            html += """<td>%s</td>""" % str(a[13])
            html += """<td>%s</td>""" % str(a[14])
            html += """<td>%s</td>""" % str(a[15])
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

class Registro:
    def __init__(self, codigo):
        self.hora = "{}".format(datetime.datetime.now().strftime("%H:%M:%S"))
        self.codigo = codigo
        self.rutaPDF = ""
        self.intersectaPE = "No"
        self.intersectaCRF = "No"
        self.intersectaAV = "No"
        self.homologacion = ""
        self.formato = ""
        self.orientacion = ""
        self.escala = ""
        self.estado = "No generado"
        self.motivoRechazo = ""

class InfoMarco:
    def __init__(self, codigo, config):
        self.urlManzanas        = 'https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/1'
        self.urlSecciones_RAU   = 'https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/2'
        self.urlSecciones_Rural = 'https://gis.ine.cl/public/rest/services/ESRI/servicios/MapServer/0'
        self.urlAreaDestacada   = 'https://gis.ine.cl/public/rest/services/ESRI/areas_destacadas/MapServer/0'
        self.urlPE          = 'https://gis.ine.cl/public/rest/services/ESRI/areas_de_rechazo1/MapServer/0'
        self.urlAV          = 'https://gis.ine.cl/public/rest/services/ESRI/areas_de_rechazo1/MapServer/1'
        self.urlCRF         = 'https://gis.ine.cl/public/rest/services/ESRI/areas_de_rechazo1/MapServer/2'
        self.urlHomologacion= 'https://gis.ine.cl/public/rest/services/ESRI/areas_de_rechazo1/MapServer/3'
        self.nombreCampoIdHomologacion = "MANZENT_MM2014"
        self.nombreCampoTipoHomologacion = "TIPO_HOMOLOGACIÓN"
        self.nombreCampoTotalViviendas = "TOT_VIV_PART_PC2016"
        self.leeConfiguracion(codigo, config)

    def leeConfiguracion(self, codigo, config):
        for marco in config['marcos']:
            if marco['id'] == codigo:
                self.urlManzanas =         marco['config']['urlManzanas']
                self.urlSecciones_RAU =    marco['config']['urlSecciones_RAU']
                self.urlSecciones_Rural =  marco['config']['urlSecciones_Rural']
                self.urlAreaDestacada =    marco['config']['urlAreaDestacada']
                self.urlPE =               marco['config']['urlPE']
                self.urlAV =               marco['config']['urlAV']
                self.urlCRF =              marco['config']['urlCRF']
                self.urlHomologacion =     marco['config']['urlHomologacion']
                self.nombreCampoIdHomologacion = marco['config']['nombreCampoIdHomologacion']
                self.nombreCampoTipoHomologacion = marco['config']['nombreCampoTipoHomologacion']
                self.nombreCampoTotalViviendas = marco['config']['nombreCampoTotalViviendas']

arcpy.env.overwriteOutput = True

urlConfiguracion   = 'https://gis.ine.cl/croquis/configuracion_dev.json'
urlComunas2016   = 'https://gis.ine.cl/croquis/ubicacion/comunas_2016.json'
urlProvincias2016   = 'https://gis.ine.cl/croquis/ubicacion/provincias_2016.json'
urlRegiones2016  = 'https://gis.ine.cl/croquis/ubicacion/regiones_2016.json'
urlUrbanosManzana2016   = 'https://gis.ine.cl/croquis/ubicacion/urbanosManzana_2016.json'
urlUrbanosRAU2016   = 'https://gis.ine.cl/croquis/ubicacion/urbanosRAU_2016.json'
urlPortal          = 'https://gis.ine.cl/portal'
usuario = 'esri_chile'
clave = '(esrichile2018)'

config = leeJsonConfiguracion()

dictRegiones = {r['codigo']:r['nombre'] for r in config['regiones']}
dictProvincias = {r['codigo']:r['nombre'] for r in config['provincias']}
dictComunas = {r['codigo']:r['nombre'] for r in config['comunas']}
dictRangos = {r[0]:[r[1],r[2]] for r in config['rangos']}

# ---------------------- PARAMETROS DINAMICOS -------------------------
parametroEncuesta = arcpy.GetParameterAsText(0)
parametroMarco = arcpy.GetParameterAsText(1)
parametroEstrato = arcpy.GetParameterAsText(2)   # Manzana RAU Rural
parametroCodigos = arcpy.GetParameterAsText(3)
parametroViviendas = arcpy.GetParameterAsText(4)
parametroSoloAnalisis = arcpy.GetParameterAsText(5)
# ---------------------- PARAMETROS DINAMICOS -------------------------

# ---------------------- PARAMETROS EN DURO ---------------------------
"""
# --------------------------------------------------------------------
parametroCodigos = "15101021001002"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "Manzana"
parametroViviendas = ""
parametroSoloAnalisis = "si"
# --------------------------------------------------------------------
parametroCodigos = "3202200055"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "RAU"
parametroViviendas = ""
# --------------------------------------------------------------------
parametroCodigos = "2203900013"
parametroEncuesta = "ENE"
parametroMarco = "2016"
parametroEstrato = "Rural"
parametroViviendas = ""
# --------------------------------------------------------------------
"""
# ---------------------- PARAMETROS EN DURO ---------------------------
infoMarco = InfoMarco(parametroMarco, config)
listaCodigos = generaListaCodigos(parametroCodigos)
listaViviendasEncuestar = generaListaCodigos(parametroViviendas)
f = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
registros = []

mensaje("Estrato: {}".format(parametroEstrato))

if parametroEstrato == "Manzana":
    diccionario = {r['codigo']:r['nombre'] for r in config['urbanosManzana']}
elif parametroEstrato == "RAU":
    diccionario = {r['codigo']:r['nombre'] for r in config['urbanosRAU']}

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

rutaCSV = escribeCSV(registros,f)
rutaZip = comprime(registros, rutaCSV,f)
arcpy.SetParameterAsText(6, rutaZip)

mensaje("El GeoProceso ha terminado correctamente")
enviarMail(registros,f)

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

""" def generaMensajeProceso(registro):
    m = []
    m.append(registro.homologacion)
    m.append(registro.intersectaPE)
    m.append(registro.intersectaCRF)
    m.append()
    if registro.intersectaPE == "Si":
        m.append("Intersecta con PE")
    if registro.intersectaCRF == "Si":
        m.append("Intersecta con CRF")
    return ", ".join(m) """
