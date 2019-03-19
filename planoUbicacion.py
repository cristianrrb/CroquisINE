# -*- coding: iso-8859-1 -*-
import arcpy
import os
import datetime
import csv
import sys
import requests
import urllib2, urllib
import json
from util import *

class PlanoUbicacion:

    def __init__(self, parametros, config, infoMarco, listaCodigos, controlTemplates, dic, controlPDF, token):
        self.parametros = parametros
        self.config = config
        self.infoMarco = infoMarco
        self.listaCodigos = listaCodigos
        self.dic = dic
        self.controlTemplates = controlTemplates
        self.token = token
        self.dictCamposId = {"Manzana": "MANZENT", "RAU": "CU_SECCION", "Rural": "CU_SECCION"}
        self.tiempo = ""
        self.controlPDF = controlPDF

    def procesa(self):
        self.tiempo = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
        registros = []
        registro = Registro(self.listaCodigos)
        try:
            if self.parametros.Estrato == "Manzana":
                entidad, extent_PU, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlManzanas, self.infoMarco.urlLUC)
                mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extent_PU)

                # validacion escala
                if escala > 7500:
                    mensaje("Escala es > 7500, Zoom a FC ListadoPoligonos")
                    desc = arcpy.Describe(fc)
                    extentFC = desc.extent
                    mensaje(extentFC)
                    mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extentFC)
                    mensaje(escala)
                    zoom(mxd, extentFC, escala)
                else:
                    mensaje("Escala es < 7500, Zoom a Urbano")
                    mensaje(escala)
                    zoom(mxd, extent_PU, escala)
                self.dic.dictUrbano = {r['codigo']:r['nombre'] for r in self.config['urbanosManzana']}
                self.actualizaVinetaManzanas_PlanoUbicacion(mxd, entidad)

            if self.parametros.Estrato == "RAU":
                entidad, extent_PU, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlSecciones_RAU, self.infoMarco.urlLUC)
                mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extent_PU)
                self.dic.dictUrbano = {r['codigo']:r['nombre'] for r in self.config['urbanosRAU']}
                self.actualizaVinetaSeccionRAU_PlanoUbicacion(mxd, entidad)
                zoom(mxd, extent_PU, escala)
            if self.parametros.Estrato == "Rural":
                entidad, extent_PU, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlSecciones_Rural, self.infoMarco.urlComunas)
                mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(self.parametros.Estrato, extent_PU)
                self.dic.dictComunas = {r['codigo']:r['nombre'] for r in self.config['comunas']}
                self.actualizaVinetaSeccionRural_PlanoUbicacion(mxd, entidad)
                zoom(mxd, extent_PU, escala)
                #pol = entidad[0]
                #comu = entidad[4]
                self.preparaMapa_PU(mxd, entidad)
                mensaje("paso por preparaMapa_PU")

            self.destacaListaPoligonos(mxd, fc)
            nombrePDF = self.generaNombrePDFPlanoUbicacion(entidad)
            mensaje(nombrePDF)
            rutaPDF = self.controlPDF.generaRutaPDF(nombrePDF, entidad)
            mensaje(rutaPDF)

            #registro.rutaPDF = generaPDF(mxd, nombrePDF, "", self.parametros, self.dic, self.config)
            registro.rutaPDF = self.controlPDF.generaPDF(mxd, rutaPDF)

            registro.formato = infoMxd['formato']
            registro.orientacion = infoMxd['orientacion']
            registro.escala = escala
            if registro.rutaPDF != "":
                registro.estado = "Plano Ubicacion"
                registro.motivo = "Croquis generado"
        except Exception:
            mensaje("Error en procesa")
            registro.estado = "Plano Ubicacion"
            registro.motivo = "Croquis No generado"

        registros.append(registro)

        nombreCsv = 'Reporte_log_PlanoUbicacion_{}_{}.csv'.format(self.parametros.Encuesta, self.tiempo)
        rutaCsv = self.escribeCSV(nombreCsv, registros)

        nombreZip = 'Comprimido_PlanoUbicacion_{}_{}.zip'.format(self.parametros.Encuesta, self.tiempo)
        rutaZip = comprime(nombreZip, registros, rutaCsv)

        return rutaZip

    def obtieneInfoParaPlanoUbicacion(self, urlEstrato, urlPlano):
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

            if self.parametros.Estrato == "Manzana":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT','MANZ']
            elif self.parametros.Estrato == "RAU":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION','CU_SECCION']
            elif self.parametros.Estrato == "Rural":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'CUT', 'COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']

            lista = []
            with arcpy.da.SearchCursor(fs, fields) as rows:
                lista = [r for r in rows]
            if len(lista) > 0:
                extent_PU = self.obtieneExtent_PU(urlPlano, lista[0][0])
                mensaje("** OK en obtieneInfoPara_PlanoUbicacion")
                return lista[0], extent_PU, fc
            else:
                mensaje("** Advertencia en obtieneInfoPara_PlanoUbicacion")
        except:
            mensaje("** Error en obtieneInfoPara_PlanoUbicacion")
        return None, None, None

    def obtieneExtent_PU(self, urlPlano, poligono):
        try:
            polygonBuffer = poligono.buffer(-10)
            polygonBufferNew = arcpy.Polygon(polygonBuffer.getPart(0), poligono.spatialReference)

            url = "{}/query".format(urlPlano)

            # ****************************************** OBTIENE EXTENT PU ****************************************
            params = {
                'token': self.token,
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

            #respuesta = requests.post(url, data=params)
            if j.has_key('extent'):
                je = j['extent']
                extentPU = arcpy.Extent(je['xmin'], je['ymin'], je['xmax'], je['ymax'])
            # ****************************************** OBTIENE EXTENT PU ****************************************
            mensaje("OK obtieneExtent_PU")
            return extentPU
        except Exception:
            mensaje("Error obtieneExtent_PU")
            arcpy.AddMessage(sys.exc_info()[1].args[0])
        return None

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
            mensaje("Se actualizaron las vinetas para manzana Plano Ubicacion.")
        except:
            mensaje("No se pudo actualizar las vinetas para manzana Plano Ubicacion.")

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
            mensaje("Se actualizaron las vinetas para RAU Plano Ubicacion.")
        except:
            mensaje("No se pudo actualizar las vinetas para RAU Plano Ubicacion.")

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
            mensaje("Se actualizaron las vinetas para Rural Plano Ubicacion.")
        except:
            mensaje("No se pudo actualizar las vinetas para Rural Plano Ubicacion.")

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
            if self.parametros.Estrato == "Manzana":
                sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr1.lyr")
            else:
                sourceLayer = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr2.lyr")
            arcpy.mapping.UpdateLayer(df, tm_layer, sourceLayer, True)
            arcpy.mapping.AddLayer(df, tm_layer, "TOP")
            mensaje("Entidades Destacadas")
        except:
            mensaje("No se pudo destacar entidades")

    def generaNombrePDFPlanoUbicacion(self, datosEntidad):
        try:
            tipo = "PU"
            if self.parametros.Estrato == "Manzana":
                descripcionUrbano = self.controlPDF.normalizaPalabra(self.dic.nombreUrbano(datosEntidad[5]))
                nombre = "{}_{}_{}{}.pdf".format(tipo, descripcionUrbano, self.parametros.Encuesta, self.parametros.Marco[2:4])
            elif self.parametros.Estrato == "RAU":
                descripcionUrbano = self.controlPDF.normalizaPalabra(self.dic.nombreUrbano(datosEntidad[5]))
                nombre = "{}_{}_{}{}_{}_{}.pdf".format(int(datosEntidad[6]), descripcionUrbano, self.parametros.Encuesta, self.parametros.Marco[2:4], tipo, self.parametros.Estrato)
            elif self.parametros.Estrato == "Rural":
                descripcionComuna = self.controlPDF.normalizaPalabra(self.dic.nombreComuna(datosEntidad[4]))
                mensaje(descripcionComuna)
                nombre = "{}_{}_{}{}_{}_R.pdf".format(int(datosEntidad[5]), descripcionComuna, self.parametros.Encuesta, self.parametros.Marco[2:4], tipo)
            mensaje("Se Genera Nombre PDF Plano Ubicacion")
            return nombre
        except:
            mensaje("No se logro Generar Nombre PDF Plano Ubicacion")

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

    def preparaMapa_PU(self, mxd, entidad):
        mensaje("preparaMapa_PU")
        poligono = self.limpiaMapa_PU(mxd, entidad)
        if poligono != None:
            lista = [m['nombre'] for m in self.config['estratos']]
            mensaje(lista)
            lista_etiquetas = [m for m in self.config['estratos'][2]['capas_labels_plano_ubicacion']]
            mensaje("Inicio preparacion de etiquetas Rural.")
            for capa in lista_etiquetas:
                self.cortaEtiqueta(mxd, capa, poligono)
            mensaje("Fin preparacion de etiquetas.")
            return True
        mensaje("No se completo la preparacion del mapa para seccion Rural.")
        return False

    # limpiaMapaRural_PU(mxd, poligonoPlano, nombreCapa)
    #
    def limpiaMapa_PU(self, mxd, entidad):
        try:
            mensaje("Limpieza de mapa 'Comuna Rural' iniciada.")
            poligonoEntrada = self.filtraComunaEnMapa(int(entidad[4]), mxd)

            lyr = self.creaLayerParaMascara(mxd)
            polchico = self.generaMascara(mxd, poligonoEntrada, lyr)

            #dfEsquicio = arcpy.mapping.ListDataFrames(mxd)[1]
            #lyr1 = arcpy.mapping.ListLayers(mxd, "Comuna", dfEsquicio)[0]
            #lyr1.definitionQuery = sql_exp

            #lyr2 = arcpy.mapping.ListLayers(mxd, "COMUNA_ADYACENTE", df)[0]
            #sql_exp = """{0} <> '{1}'""".format(arcpy.AddFieldDelimiters(lyr2.dataSource, "COMUNA"), int(entidad[4]))
            #lyr2.definitionQuery = sql_exp

            mensaje("Limpieza de mapa correcta.")
            return polchico

        except Exception:
            mensaje(sys.exc_info()[1].args[0])
            mensaje("Error en limpieza de mapa 'Comuna Rural'.")
        return None

    def filtraComunaEnMapa(self, codigoComuna, mxd):
        poligono = None
         # Filtra comuna en mapa
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        lyrComuna = arcpy.mapping.ListLayers(mxd, "Comuna", df)[0]
        sql_exp = """{0} = {1}""".format(arcpy.AddFieldDelimiters(lyrComuna.dataSource, "COMUNA"), codigoComuna)
        lyrComuna.definitionQuery = sql_exp

        cursor = arcpy.da.SearchCursor(lyrComuna, ['SHAPE@'])
        for row in cursor:
            poligono = row[0]
        del cursor
        return poligono

    def generaMascara(self, mxd, poligonoEntrada, lyr):
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        poligonoProyectado = poligonoEntrada.projectAs(df.spatialReference)

        distancia = float(calculaDistanciaBufferRural(poligonoProyectado.area).replace(" Meters", ""))

        polgrande = poligonoProyectado.buffer(distancia * 100)
        polchico = poligonoProyectado.buffer(distancia)

        poligonoMascara = polgrande.difference(polchico)

        cursor = arcpy.da.InsertCursor(lyr, ['SHAPE@', "TIPO"])
        cursor.insertRow([poligonoMascara, 0])
        del cursor
        return polchico

    def creaLayerParaMascara(self, mxd):
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        fc = arcpy.CreateFeatureclass_management("in_memory", "FC1", "POLYGON", "", "DISABLED", "DISABLED", df.spatialReference, "", "0", "0", "0")
        arcpy.AddField_management(fc, "tipo", "LONG")

        tmpLyr = os.path.join("in_memory", "graphic_lyr")
        arcpy.MakeFeatureLayer_management(fc, tmpLyr)
        lyr = arcpy.mapping.Layer(tmpLyr)

        sourceLyr = arcpy.mapping.Layer(r"C:\CROQUIS_ESRI\Scripts\graphic_lyr.lyr")
        arcpy.mapping.UpdateLayer(df, lyr, sourceLyr, True)

        # del fc
        arcpy.mapping.AddLayer(df, lyr, "TOP")
        return lyr

    def listaEtiquetas_PU(self):
        return [m for m in self.config['estratos'][2]['capas_labels_plano_ubicacion']]

    def cortaEtiqueta(self, mxd, elLyr, poly):
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
