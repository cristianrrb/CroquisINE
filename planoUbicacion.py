# -*- coding: iso-8859-1 -*-
import arcpy
import os
import datetime
import csv
import requests
from util import mensaje, zoom, generaPDF2, comprime, normalizaPalabra, Registro

class PlanoUbicacion:

    def __init__(self, parametros, config, infoMarco, listaCodigos, controlTemplates, dic, token):
        self.parametros = parametros
        self.config = config
        self.infoMarco = infoMarco
        self.listaCodigos = listaCodigos
        self.dic = dic
        self.controlTemplates = controlTemplates
        self.token = token
        self.dictCamposId = {"Manzana": "MANZENT", "RAU": "CU_SECCION", "Rural": "CU_SECCION"}
        self.tiempo = ""

    def procesa(self):
        self.tiempo = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
        registros = []
        registro = Registro(self.listaCodigos)
        try:
            if self.parametros.Estrato == "Manzana":
                entidad, extent, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlManzanas, self.infoMarco.urlLUC)
                mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extent)
                self.dic.dictUrbano = {r['codigo']:r['nombre'] for r in self.config['urbanosManzana']}
                self.actualizaVinetaManzanas_PlanoUbicacion(mxd, entidad)
            if self.parametros.Estrato == "RAU":
                entidad, extent, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlSecciones_RAU, self.infoMarco.urlLUC)
                mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extent)
                self.dic.dictUrbano = {r['codigo']:r['nombre'] for r in self.config['urbanosRAU']}
                self.actualizaVinetaSeccionRAU_PlanoUbicacion(mxd, entidad)
            if self.parametros.Estrato == "Rural":
                entidad, extent, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlSecciones_Rural, self.infoMarco.urlComuna)
                mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extent)
                self.actualizaVinetaSeccionRural_PlanoUbicacion(mxd, entidad)

            self.destacaListaPoligonos(mxd, fc)
            zoom(mxd, extent, escala)

            nombrePDF = self.generaNombrePDFPlanoUbicacion(infoMxd)
            mensaje(nombrePDF)
            rutaPDF = self.generaRutaPDF(nombrePDF)
            mensaje(rutaPDF)

            #registro.rutaPDF = generaPDF(mxd, nombrePDF, "", self.parametros, self.dic, self.config)
            registro.rutaPDF = generaPDF2(mxd, rutaPDF)

            registro.formato = infoMxd['formato']
            registro.orientacion = infoMxd['orientacion']
            registro.escala = escala
            if registro.rutaPDF != "":
                registro.estado = "Plano Ubicacion"
                registro.motivo = "Croquis generado"
        except:
            registro.estado = "Plano Ubicacion"
            registro.motivo = "Croquis NO generado"

        registros.append(registro)

        nombreCsv = 'Reporte_log_PlanoUbicacion_{}_{}.csv'.format(self.parametros.Encuesta, self.tiempo)
        rutaCsv = self.escribeCSV(nombreCsv, registros)

        nombreZip = 'Comprimido_PlanoUbicacion_{}_{}.zip'.format(self.parametros.Encuesta, self.tiempo)
        rutaZip = comprime(nombreZip, registros, rutaCsv)

        return rutaZip

    def generaRutaPDF(self, nombrePDF):
        destinoPDF = ""
        try:
            rutaDestino = os.path.join(self.config['rutabase'], "MUESTRAS_PDF", self.parametros.Encuesta, "PLANOS_UBICACION")
            if not os.path.exists(rutaDestino):
                os.makedirs(rutaDestino)
            destinoPDF = os.path.join(rutaDestino, nombrePDF)
            mensaje(rutaDestino)
        except:
            mensaje("No se pudo crear Ruta Destino PDF ")
        return destinoPDF

    def obtieneInfoParaPlanoUbicacion(self, urlEstrato, urlPlano):
    #def obtieneInfoParaPlanoUbicacion(self, urlServicio):
        lista = []
        try:
            condiciones = []
            for codigo in self.listaCodigos:
                condicion = "{}+%3D+{}".format(self.dictCamposId[self.parametros.Estrato], codigo)
                condiciones.append(condicion)

            query = " + OR +".join(condiciones)
            url = '{}/query?token={}&where={}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'

            fs = arcpy.FeatureSet()
            fs.load(url.format(urlEstrato, self.token, query))

            fc = os.path.join("in_memory", "fc")
            fs.save(fc)

            desc = arcpy.Describe(fc)
            extent = desc.extent

            mensaje(extent)

            if self.parametros.Estrato == "Manzana":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT','MANZ']
            elif self.parametros.Estrato == "RAU":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION','CU_SECCION']
            elif self.parametros.Estrato == "Rural":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'CUT', 'COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']

            with arcpy.da.SearchCursor(fs, fields) as rows:
                lista = [r for r in rows]
            #mensaje(len(lista[0]))
            extent = obtieneExtentUrbano(urlPlano, lista[0][0])

            mensaje("** OK en obtieneInfoPara_PlanoUbicacion")
        except:
            mensaje("** Error en obtieneInfoPara_PlanoUbicacion")
        return lista[0], extent, fc

    def obtieneExtentUrbano(self, urlUrbano, poligono):
        url = "{}/query".format(urlUrbano)
        params = {
            'token': self.token,
            'f':'json',
            'where':'1=1',
            'returnExtentOnly':'true',
            'geometry':jpoligon,
            'geometryType':'esriGeometryPolygon'
        }
        r = requests.post(url, data=params)
        j = r.json()
        extent = j['extent']
        return extent

    def actualizaVinetaManzanas_PlanoUbicacion(self, mxd, entidad):
        try:
            nombre_region = self.dic.nombreRegion(entidad[2])
            nombre_provincia = self.dic.nombreProvincia(entidad[3])
            nombre_comuna = self.dic.nombreComuna(entidad[4])
            nombre_urbano = self.dic.nombreUrbano(entidad[5])

            for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
                if self.parametros.Encuesta == "ENE":
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta
                else:
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta + " " + self.parametros.Marco
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

    def actualizaVinetaSeccionRAU_PlanoUbicacion(self, mxd, datosRAU):
        try:
            nombre_region = self.dic.nombreRegion(datosRAU[2])
            nombre_provincia = self.dic.nombreProvincia(datosRAU[3])
            nombre_comuna = self.dic.nombreComuna(datosRAU[4])
            nombre_urbano = self.dic.nombreUrbano(datosRAU[5])

            for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
                if self.parametros.Encuesta == "ENE":
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta
                else:
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta + " " + self.parametros.Marco
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

    def actualizaVinetaSeccionRural_PlanoUbicacion(self, mxd, datosRural):
        try:
            nombre_region = self.dic.nombreRegion(datosRural[2])
            nombre_provincia = self.dic.nombreProvincia(datosRural[3])
            nombre_comuna = self.dic.nombreComuna(datosRural[4])

            for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
                if self.parametros.Encuesta == "ENE":
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta
                else:
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta + " " + self.parametros.Marco
                if elm.name == "Nombre_Region":
                    elm.text = nombre_region
                if elm.name == "Nombre_Provincia":
                    elm.text = nombre_provincia
                if elm.name == "Nombre_Comuna":
                    elm.text = nombre_comuna
            mensaje("Se actualizaron las viñetas para Rural Plano Ubicacion.")
        except:
            mensaje("No se pudo actualizar las viñetas para Rural Plano Ubicacion.")

    def destacaListaPoligonos(self, mxd, fc):
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
            sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr2.lyr")
            arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
            arcpy.mapping.AddLayer(df, tm_layer, "TOP")
            mensaje("Entidades Destacadas")
        except:
            mensaje("No se pudo destacar entidades")

    def generaNombrePDFPlanoUbicacion(self, infoMxd):
        f = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
        if self.parametros.Estrato == "Manzana":
            tipo = "MZ_Plano_Ubicacion_" + str(f)
            nombre = "{}_{}_{}_{}_{}.pdf".format(tipo, infoMxd['formato'], infoMxd['orientacion'], self.parametros.Encuesta, self.parametros.Marco[2:4])
        elif self.parametros.Estrato == "RAU":
            tipo = "RAU_Plano_Ubicacion_" + str(f)
            nombre = "{}_{}_{}_{}_{}.pdf".format(tipo, infoMxd['formato'], infoMxd['orientacion'], self.parametros.Encuesta, self.parametros.Marco[2:4])
        elif self.parametros.Estrato == "Rural":
            tipo = "Rural_Plano_Ubicacion_" + str(f)
            nombre = "{}_{}_{}_{}_{}.pdf".format(tipo, infoMxd['formato'], infoMxd['orientacion'], self.parametros.Encuesta, self.parametros.Marco[2:4])
        return nombre

    def escribeCSV(self, nombreCsv, registros):
        try:
            rutaCsv = os.path.join(self.config['rutabase'], "LOG", nombreCsv)
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


""" params = {
    'where':'1=1',
    #'text':'',
    #'objectIds':'',
    #'time':'',
    'geometry':geometry,
    'geometryType':'esriGeometryPolygon',
    #'inSR':'',
    'spatialRel':'esriSpatialRelIntersects',
    #'relationParam':'',
    #'outFields':'',
    'returnGeometry':'false',
    'returnTrueCurves':'false',
    #'maxAllowableOffset':'',
    #'geometryPrecision':'',
    #'outSR':'',
    #'having':'',
    'returnIdsOnly':'true',
    'returnCountOnly':'false',
    #'orderByFields':'',
    #'groupByFieldsForStatistics':'',
    #'outStatistics':'',
    'returnZ':'false',
    'returnM':'false',
    #'gdbVersion':'',
    #'historicMoment':'',
    'returnDistinctValues':'false',
    #'resultOffset':'',
    #'resultRecordCount':'', 
    #'queryByDistance':'',
    'returnExtentOnly':'false',
    #'datumTransformation':'',
    #'parameterValues':'',
    #'rangeValues':'',
    #'quantizationParameters':'',
    'f': 'pjson'
} """
