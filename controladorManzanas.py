# -*- coding: iso-8859-1 -*-
import arcpy
import os
import datetime
import csv
import sys
# import requests
import urllib
import urllib2
import json
from util import *

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class ControladorManzanas:

    def __init__(self, parametros, config, infoMarco, listaCodigos, controlTemplates, dic, controlPDF, token):
        self.parametros = parametros
        self.config = config
        self.infoMarco = infoMarco
        self.listaCodigos = listaCodigos
        self.dic = dic
        self.controlTemplates = controlTemplates
        self.token = token
        # self.dictCamposId = {"Manzana": "MANZENT", "RAU": "CU_SECCION", "Rural": "CU_SECCION"}
        self.tiempo = ""
        self.controlPDF = controlPDF
        self.registros = []
        self.dictRangos = {r[0]:[r[1],r[2]] for r in self.config['rangos']}

    def procesa(self):
        self.horaInicio = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
        self.dic.dictUrbano = {r['codigo']:r['nombre'] for r in self.config['urbanosManzana']}
        listaViviendasEncuestar = generaListaCodigos(self.parametros.Viviendas)   # util

        for indice, codigo in enumerate(self.listaCodigos):
            viviendas = -1
            if len(listaViviendasEncuestar) > 0:
                viviendas = listaViviendasEncuestar[indice]
            self.procesaManzana(codigo, viviendas)

        rutaCSV = self.escribeCSV()
        rutaZip = comprime(self.nombreZip(), self.registros, rutaCSV)  # util

        self.enviarMail()

        return rutaZip

    def procesaManzana(self, codigo, viviendasEncuestar):
        try:
            ############################################################## [INICIO SECCION ANALISIS DE MANZANA] #####################################################################
            registro = Registro(codigo)

            registro.homologacion, totalViviendas = self.obtieneHomologacion(codigo)
            resultado = self.validaRangoViviendas(viviendasEncuestar, totalViviendas, registro)

            datosManzana, extent = self.obtieneInfoManzana(codigo)
            area_polygon2017 = self.intersectaManzanaCenso2017(datosManzana[0])

            self.comparaManzanas(datosManzana[1], area_polygon2017, registro)

            if datosManzana != None:
                registro.intersectaPE = intersectaConArea(datosManzana[0], self.infoMarco.urlPE)  # util
                registro.intersectaAV = intersectaConArea(datosManzana[0], self.infoMarco.urlAV)  # util
                registro.intersectaCRF = intersectaConArea(datosManzana[0], self.infoMarco.urlCRF)  # util
            ############################################################## [FIN SECCION ANALISIS DE MANZANA] #####################################################################

                if not (registro.estadoViviendas == "Rechazado" or self.parametros.SoloAnalisis == 'si'):
                    mxd, infoMxd, escala = self.controlTemplates.buscaTemplateManzana(extent)
                    if mxd != None:
                        if self.preparaMapaManzana(mxd, extent, escala, datosManzana):
                            mensaje("Registrando la operacion.")
                            registro.formato = infoMxd['formato']
                            registro.orientacion = infoMxd['orientacion']
                            registro.escala = escala
                            registro.codigoBarra = self.generaCodigoBarra(datosManzana)

                            nombrePDF = self.generaNombrePDF(datosManzana, infoMxd)
                            mensaje(nombrePDF)
                            rutaPDF = self.controlPDF.generaRutaPDF(nombrePDF, datosManzana)
                            mensaje(rutaPDF)
                            registro.rutaPDF = self.controlPDF.generaPDF(mxd, rutaPDF)

                            if registro.rutaPDF != "":
                                registro.estado = "Genera PDF"
                                registro.motivo = "Croquis generado"
                            else:
                                registro.estado = "Genera PDF"
                                registro.motivo = "Croquis No generado"

                # ************************** inicio if para solo para analisis cuando se Rechaza la manzana *********************************
                elif self.parametros.SoloAnalisis == "si":
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
                registro.homologacion = ""
        except:
            registro.estado = "Error procesaManzana"
            registro.motivo = "Croquis No generado"
            registro.estadoViviendas = ""
            registro.motivoViviendas = ""
            registro.intersectaPE = ""
            registro.intersectaCRF = ""
            registro.intersectaAV = ""
            registro.homologacion = ""
            mensaje("Error: no se completo el proceso de Manzana.")

        self.mensajeEstado(registro)
        self.registros.append(registro)
        return

    def leeNombreCapa(self, estrato):
        #d = {"Manzana":0,"RAU":1,"Rural":2}
        lista = ""
        for e in self.config['estratos']:
            if e['nombre'] == estrato:
                lista = e['nombre_capa']
        return lista

    def listaEtiquetas(self, estrato):
        d = {"Manzana":0,"RAU":1,"Rural":2}
        lista = []
        for e in self.config['estratos']:
            if e['nombre'] == estrato:
                lista = [m for m in self.config['estratos'][d[estrato]]['capas_labels']]
        return lista

    def obtieneHomologacion(self, codigo):
        try:
            campos = "*"
            queryURL = "{}/query".format(self.infoMarco.urlHomologacion)
            params = {
                'token': self.token,
                'f':'json',
                'where':'{}={}'.format(self.infoMarco.nombreCampoIdHomologacion, codigo),
                'outFields': campos
            }
            req = urllib2.Request(queryURL, urllib.urlencode(params))
            response = urllib2.urlopen(req)
            valores = json.load(response)
            atributos = valores['features'][0]['attributes']
            return atributos[self.infoMarco.nombreCampoTipoHomologacion], atributos[self.infoMarco.nombreCampoTotalViviendas]
        except:
            pass
        return "", -1

    def validaRangoViviendas(self, viviendasEncuestar, totalViviendas, registro):
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
            if self.dictRangos.has_key(viviendasEncuestar):
                rango = self.dictRangos[viviendasEncuestar]
                if rango[0] <= totalViviendas <= rango[1]:
                    mensaje("Viviendas a Encuestar. ({})".format(viviendasEncuestar))
                    mensaje("Rango MÃ³nimo/MÃ³ximo. ({},{})".format(rango[0], rango[1]))
                    mensaje("Total Viviendas. ({})".format(totalViviendas))
                    mensaje("Se cumple con el rango de viviendas de la manzana.")
                    registro.estadoViviendas = "Correcto"
                    registro.motivoViviendas = "Se cumple con el rango de viviendas de la manzana"
                    return "Correcto"
                else:
                    mensaje("Viviendas a Encuestar. ({})".format(viviendasEncuestar))
                    mensaje("Rango MÃ³nimo/MÃ³ximo. ({},{})".format(rango[0],rango[1]))
                    mensaje("Total Viviendas. ({})".format(totalViviendas))
                    mensaje("No se cumple con el rango de viviendas de la manzana. ({} => [{},{}])".format(totalViviendas, rango[0], rango[1]))

                    registro.estadoViviendas = "Rechazado"
                    registro.motivoViviendas = "No se cumple con el rango de viviendas de la manzana"
                    return "Rechazado"
            else:    # no existe el rango
                mensaje("No esta definido el rango para evaluacion de cantidad de viviendas a encuestar. ({})".format(viviendasEncuestar))

    def obtieneInfoManzana(self, codigo):
        try:
            url = '{}/query?token={}&where=MANZENT+%3D+{}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'
            fs = arcpy.FeatureSet()
            fs.load(url.format(self.infoMarco.urlManzanas, self.token, codigo))

            fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT','MANZ']

            with arcpy.da.SearchCursor(fs, fields) as rows:
                lista = [r for r in rows]

            if  lista != None and len(lista) == 1:
                metrosBuffer = calculaDistanciaBufferManzana(lista[0][1])  # util
                extent = calculaExtent(fs, metrosBuffer)  # util
                mensaje('Datos de manzana obtenidos correctamente.')
                return lista[0], extent
            else:
                mensaje("** El registro de manzana no existe")

                return None, None
        except:
            mensaje("** Error en obtieneInfoManzana")
            return None, None

    # comprueba si poligono2016 intersecta con poligono2017
    def intersectaManzanaCenso2017(self, poligono2016):
        try:
            polygonBuffer = poligono2016.buffer(10)
            polygonBufferNew = arcpy.Polygon(polygonBuffer.getPart(0), poligono2016.spatialReference)
            params = {'f':'json', 'where':'1=1', 'outFields':'*',  'geometry':polygonBufferNew.JSON, 'geometryType':'esriGeometryPolygon',
                    'spatialRel':'esriSpatialRelContains', 'inSR':'WGS_1984_Web_Mercator_Auxiliary_Sphere',
                    'outSR':'WGS_1984_Web_Mercator_Auxiliary_Sphere'}
            queryURL = "{}/query".format(self.infoMarco.urlManzanasCenso2017)
            req = urllib2.Request(queryURL, urllib.urlencode(params))
            response = urllib2.urlopen(req)
            ids = json.load(response)

            pols = []
            polygonOriginal = polygonBufferNew.buffer(-10)
            for pol in ids["features"]:
                polygon = arcpy.AsShape(pol["geometry"], True)
                area_polygon2017 = polygon.area
                mensaje(polygonOriginal.contains(polygon, "PROPER"))
                if polygonOriginal.contains(polygon, "PROPER"):
                    pols.append(polygon)
            if len(pols) > 0:
                mensaje("polygono2016 Intersecta con {} en censo2017".format(len(pols)))
                return area_polygon2017
            else:
                return None
        except:
            mensaje('** Error en intersectaManzanaCenso2017.')
        return ""

    def comparaManzanas(self, manzana2016, manzana2017, registro):
        try:
            mensaje("area_manzana2016 = {}".format(manzana2016))
            mensaje("area_manzana2017 = {}".format(manzana2017))
            if manzana2017 != None:
                diferencia = abs(manzana2016 -  manzana2017)

                porcentaje = int(round((diferencia/manzana2016)*100,0))
                mensaje("Porcentaje de Diferencia = {}".format(porcentaje))

                if porcentaje <= 5:
                    estadoSuperficie = "OK"
                    motivoSuperficie = "Diferencia en superficie es menor a 5 porciento"
                    mensaje("OK: Diferencia en superficie es menor a 5 porciento")
                elif porcentaje >= 6 and porcentaje <= 40:
                    estadoSuperficie = "Alerta"
                    motivoSuperficie = "Diferencia en superficie entre 6 y 40 porciento"
                    mensaje("Alerta: Diferencia en superficie entre 6 y 40 porciento")
                elif porcentaje > 40:
                    estadoSuperficie = "Rechazada"
                    motivoSuperficie = "Diferencia en superficie supera 40 porciento"
                    mensaje("Rechazada: Diferencia en superficie supera 40 porciento")
            else:
                estadoSuperficie = "No encontrada"
                motivoSuperficie = "Manzana no encontrada en Censo2017"
                mensaje("No encontrada: Manzana no encontrada en Censo2017")
        except:
            estadoSuperficie = "Error"
            motivoSuperficie = "Error: Al comparar Manzanas"
            mensaje("Error: Al comparar Manzanas")

        registro.estadoSuperficie = estadoSuperficie
        registro.motivoSuperficie = motivoSuperficie
        registro.area_manzana2016 = manzana2016
        registro.area_manzana2017 = manzana2017
        return estadoSuperficie, motivoSuperficie

    def preparaMapaManzana(self, mxd, extent, escala, datosManzana):
        self.actualizaVinetaManzanas(mxd, datosManzana)
        if zoom(mxd, extent, escala):
            poligono = self.limpiaMapaManzana(mxd, datosManzana[0], int(datosManzana[10]))
            if poligono != None:
                lista_etiquetas = self.listaEtiquetas("Manzana")
                mensaje("Inicio preparacion de etiquetas Manzana.")
                for capa in lista_etiquetas:
                    cortaEtiqueta(mxd, capa, poligono)
                mensaje("Fin preparacion de etiquetas.")
                return True
        mensaje("No se completo la preparacion del mapa para manzana.")
        return False

    def generaCodigoBarra(self, datosEntidad):
        nombre = "*MZ-{}-{}-{}-{}*".format(int(datosEntidad[6]), int(datosEntidad[11]), self.parametros.Encuesta, self.parametros.Marco[2:4])
        return nombre

    def generaNombrePDF(self, datosEntidad, infoMxd):
        f = "{}".format(datetime.datetime.now().strftime("%d%m%Y%H%M%S"))
        nombre = "MZ_{}_{}_{}_{}_{}_{}.pdf".format(int(datosEntidad[6]), int(datosEntidad[11]), infoMxd['formato'], infoMxd['orientacion'], self.parametros.Encuesta, self.parametros.Marco[2:4])
        return nombre

    def actualizaVinetaManzanas(self, mxd, datosManzana):
        #fields = ['SHAPE@','SHAPE@AREA','REGION','PROVINCIA','COMUNA','URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA']
        try:
            nombre_region    = self.dic.nombreRegion(datosManzana[2])
            nombre_provincia = self.dic.nombreProvincia(datosManzana[3])
            nombre_comuna    = self.dic.nombreComuna(datosManzana[4])
            nombre_urbano    = self.dic.nombreUrbano(datosManzana[5])
            codigo_barra     = self.generaCodigoBarra(datosManzana)
            mensaje(codigo_barra)

            for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
                if self.parametros.Encuesta == "ENE":
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta
                else:
                    if elm.name == "Nombre_Muestra":
                        elm.text = self.parametros.Encuesta + " " + parametroMarco
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
            mensaje("Se actualizaron las vinetas para manzana.")
        except:
            mensaje("No se pudo actualizar las vinetas para manzana.")

    def limpiaMapaManzana(self, mxd, manzana, cod_manz):
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
            dist = '15 Meters'
            dist_buff = float(dist.replace(" Meters", ""))
            polgrande = ext.buffer(dist_buff * 40)
            polchico = ext.buffer(dist_buff)
            poli = polgrande.difference(polchico)
            cursor = arcpy.da.InsertCursor(tm_layer, ['SHAPE@', "TIPO"])
            cursor.insertRow([poli,0])
            cursor.insertRow([ext,1])
            url = self.infoMarco.urlManzanas
            manz_excluidas = areasExcluidas(ext, url)
            if manz_excluidas != None:
                for manz in manz_excluidas:
                    cursor.insertRow([manz,2])
            del cursor
            del FC
            arcpy.mapping.AddLayer(df, tm_layer, "TOP")
            limpiaEsquicio(mxd, self.leeNombreCapa("Manzana"), "manzent", cod_manz)
            mensaje("Limpieza de mapa correcta.")
            return polchico
        except Exception:
            mensaje(sys.exc_info()[1].args[0])
            mensaje("Error en limpieza de mapa.")
        return None

    def escribeCSV(self):
        try:
            nombre = 'Reporte_log_MZ_{}_{}.csv'.format(self.parametros.Encuesta, self.horaInicio)
            rutaCsv = os.path.join(self.config['rutabase'], "LOG", nombre)
            mensaje("Ruta CSV :{}".format(rutaCsv))

            with open(rutaCsv, "wb") as f:
                wr = csv.writer(f, delimiter=';')
                a = ['Hora', 'Codigo', 'Estado Proceso', 'Motivo Proceso', 'Estado Superficie','Motivo Superficie','Area Manzana2016','Area Manzana2017','Estado Viviendas','Motivo Viviendas','CUT', 'CODIGO DISTRITO', 'CODIGO LOCALIDAD O ZONA', 'CODIGO ENTIDAD', 'Ruta PDF', 'Intersecta PE', 'Intersecta CRF', 'Intersecta AV', 'Homologacion', 'Formato / Orientacion', 'Escala', "Codigo barra"]
                wr.writerow(a)
                for r in self.registros:
                    cut, dis, area, loc, ent = descomponeManzent(r.codigo)  # util
                    a = [r.hora, r.codigo, r.estado, r.motivo, r.estadoSuperficie, r.motivoSuperficie, r.area_manzana2016, r.area_manzana2017, r.estadoViviendas, r.motivoViviendas, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, r.homologacion.encode('utf8'), r.formato +" / "+ r.orientacion, r.escala, r.codigoBarra.encode('utf8')]
                    wr.writerow(a)

            return rutaCsv
        except:
            return None

    def mensajeEstado(self, registro):
        homologacion = "I"
        if registro.homologacion == 'Homologada No IdÃ©ntica' or registro.homologacion == 'Homologada No IdÃ©nticas':
            homologacion = 'NI'

        # Mensajes para analisis
        if self.parametros.SoloAnalisis == "si":
            if registro.estadoViviendas == "Correcto":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estadoViviendas) # Correcto
                print(s)
                arcpy.AddMessage(s)
                mensaje("Analisis: viviendas correctas.")
            if registro.estadoViviendas == "Rechazado":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estadoViviendas) #Rechazado
                print(s)
                arcpy.AddMessage(s)
                mensaje("Analisis: Se rechazÃ³ la manzana.")
            if registro.estadoViviendas == "":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estado) #Manzana no existe
                print(s)
                arcpy.AddMessage(s)
                mensaje("Analisis: Manzana No Existe")
            return "Analisis"

        else:
            # Mensajes para Generar PDF
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

            if self.parametros.Estrato == "RAU" or self.parametros.Estrato == "Rural":
                s = "#{}#:{},{},{},{},{}".format(registro.codigo, registro.intersectaPE, registro.intersectaCRF, registro.intersectaAV, homologacion, registro.estado)
                print(s)
                arcpy.AddMessage(s)

                if registro.estado == "Correcto":
                    mensaje("Genera croquis: Se genera el croquis para Secciones")
                if registro.estado == "Incorrecto":
                    mensaje("Genera croquis: No se logrÃ³ generar el croquis para seccion.")
                if registro.estado == "Seccion No Existe":
                    mensaje("Genera croquis: No se logrÃ³ generar el croquis para seccion.")
            return "Croquis"

    def nombreZip(self):
        if self.parametros.SoloPlanoUbicacion == "Si":
            tipo = "PlanoUbicacion"
        else:
            tipo = "MZ"

        nombre = 'Comprimido_{}_{}_{}.zip'.format(tipo, self.parametros.Encuesta, self.horaInicio)
        return nombre

    def enviarMail(self):
        fromMail = "COMPLETAR"
        passwordFromMail = 'COMPLETAR'
        toMail = "reinaldo.segura@ine.cl"

        msg = MIMEMultipart('alternative')

        encuesta = self.parametros.Encuesta
        if self.parametros.Encuesta != "ENE":
            encuesta += " " + self.parametros.Marco

        msg['Subject'] = "Reporte Croquis INE Nro: {} / Encuesta: {}, Estrato: {}".format(str(self.horaInicio), encuesta, self.parametros.Estrato)
        msg['From'] = fromMail
        msg['To'] = toMail

        html = "<html>"
        mensaje("1")
        html += self._cabeceraCorreo()
        mensaje("2")
        html += "<body>"
        mensaje("3")
        html += self._cuerpoTitulo(encuesta)
        mensaje("4")
        html += self._cuerpoTabla()
        mensaje("5")
        html += self._cuerpoPie()
        mensaje("6")
        html += "</body>"
        mensaje("7")
        html += "</html>"

        try:
            msg.attach(MIMEText(html, 'html'))
            mensaje("11")
            mailserver = smtplib.SMTP('smtp.office365.com', 587)
            mensaje("22")
            mailserver.ehlo()
            mensaje("33")
            mailserver.starttls()
            mensaje("44")
            mailserver.login(fromMail, passwordFromMail)
            mensaje("55")
            mailserver.sendmail(fromMail, toMail, msg.as_string())
            mensaje("Reporte Enviado")
            mailserver.quit()
        except:
            mensaje("No se envia correo electronico de Alertas y Rechazo, Verificar cuentas de correo")

    def _cabeceraCorreo(self):
        return """
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
        """

    def _cuerpoTitulo(self, encuesta):
        html =  "<h2>Reporte Croquis INE Nro: " + str(self.horaInicio) + "</h2>"
        html += "<h3>Encuesta: " + encuesta + " / Estrato: " + str(self.parametros.Estrato) + "</h3>"
        html += "<p>Reporte croquis de alertas y rechazo para Instituto Nacional de Estadisticas de Chile</p>"
        html += "<u>Motivos de Rechazo:</u>"
        html += "<ul>"
        html += '  <li type="disc">Rechazo, Manzana con menos de 8 viviendas; Cuando "Estado" es, Rechazado.</li>'
        html += '  <li type="disc">Rechazada, Diferencia de AreaManzana_2016 y AreaManzana_Censo2017 > 40%, Cuando "Estado superficie" es, Rechazada</li>'
        html += "</ul>"
        html += "<u>Motivos de Alerta:</u>"
        html += "<ul>"
        html += '  <li type="disc">Alerta, Diferencia de AreaManzana_2016 y AreaManzana_Censo2017 se encuentra entre 6% y 40% inclusive, Cuando "Estado superficie" es, Alerta</li>'
        html += '  <li type="disc">Alerta, Manzana Intersecta con Permiso de Edificacion (PE); Cuando "Intersecta PE" es, Si.</li>'
        html += '  <li type="disc">Alerta, Manzana Intersecta con Certificado de Recepcion Final (CRF); Cuando "Intersecta CRF" es, Si.</li>'
        html += '  <li type="disc">Alerta, Manzana Intersecta con areas Verdes (AV); Cuando "Intersecta AV" es, Si.</li>'
        html += '  <li type="disc">Alerta, Manzana Homologacion No es Identica; cuando "Homologacion" es, Homologada No Identica(s)</li>'
        html += "</ul>"
        return html

    def _cuerpoTabla(self):
        mensaje("a")
        html =  '<div style="overflow-x:auto;">'
        html += '<table>'
        html += '  <tr>'
        html += '    <th></th>'
        html += '    <th>Hora</th>'
        html += '    <th>Codigo</th>'
        html += '    <th>Estado</th>'
        html += '    <th>Motivo</th>'
        html += '    <th>Estado Superficie</th>'
        html += '    <th>Motivo Superficie</th>'
        html += '    <th>Estado Viviendas</th>'
        html += '    <th>Motivo Viviendas</th>'
        html += '    <th>CUT</th>'
        html += '    <th>C.DISTRITO</th>'
        html += '    <th>C.ZONA</th>'
        html += '    <th>C.ENTIDAD</th>'
        html += '    <th>Ruta PDF</th>'
        html += '    <th>Intersecta PE</th>'
        html += '    <th>Intersecta CRF</th>'
        html += '    <th>Intersecta AV</th>'
        html += '    <th>Homologacion</th>'
        html += '    <th>Formato / Orientacion</th>'
        html += '    <th>Escala</th>'
        html += '    <th>Codigo barra<th/>'
        html += '  </tr>'

        for i, r in enumerate(self.registros, 1):
            mensaje(i)
            if self._enviaCorreo(r):
                cut, dis, area, loc, ent = descomponeManzent(r.codigo)  # util
                homologacion = r.homologacion
                if homologacion[0:16] == "Homologada No Id":
                    homologacion = "Homologada No Identica"
                if homologacion[0:13] == "Homologada Id":
                    homologacion = "Homologada Identica"
                a = [r.hora, r.codigo, r.estado, r.motivo, r.estadoSuperficie, r.motivoSuperficie, r.estadoViviendas, r.motivoViviendas, cut, dis, loc, ent, r.rutaPDF, r.intersectaPE, r.intersectaCRF, r.intersectaAV, homologacion, r.formato +" / "+ r.orientacion, r.escala, r.codigoBarra.encode('utf8')]
                html += '<tr>'
                html += "<td>{}</td>".format(i)

                for c in a:
                    html += "<td>{}</td>".format(c)

                html += '</tr>'

        html += '</table>'
        html += '</div>'

        return html

    def _enviaCorreo(self, r):
        if r.estadoViviendas == "Rechazado":
            return True

        if r.estadoSuperficie == "Alerta":
            return True

        if r.estadoSuperficie == "Rechazada":
            return True

        if r.intersectaPE == "Si":
            return True

        if r.intersectaCRF == "Si":
            return True

        if r.intersectaAV == "Si":
            return True

        if r.homologacion != "" and r.homologacion[0:16] == 'Homologada No Id':
            return True

        return False

    def _cuerpoPie(self):
        html =  '</br>'
        html += '<p><b>Departamento de Geografia</b></p>'
        html += '<p>Instituto Nacional de Estadisticas</p>'
        html += '<p>Fono: 232461860</p>'
        return html
