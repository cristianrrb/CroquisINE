# -*- coding: iso-8859-1 -*-
import arcpy
import util

class PlanoUbicacion:

    def __init__(self, parametros, config, infoMarco, listaCodigos, controlTemplates, token):
        self.parametros = parametros
        self.config = config
        self.infoMarco = infoMarco
        self.listaCodigos = listaCodigos
        self.controlTemplates = controlTemplates
        self.token = token

    def procesa(self):
        if self.parametros.Estrato == "Manzana":
            entidad, extent, fc = self.obtieneInfoParaPlanoUbicacion(self.infoMarco.urlManzanas)
            mxd, infoMxd, escala = self.controlTemplates.buscaTemplatePlanoUbicacion(extent)
            diccionario = {r['codigo']:r['nombre'] for r in config['urbanosManzana']}
            actualizaVinetaManzanas_PlanoUbicacion(mxd, entidad)
        if self.parametros.Estrato == "RAU":
            entidad, extent, fc = obtieneInfoParaPlanoUbicacion(self.infoMarco.urlSecciones_RAU)
            mxd, infoMxd, escala = controlTemplates.buscaTemplatePlanoUbicacion(extent)
            diccionario = {r['codigo']:r['nombre'] for r in config['urbanosRAU']}
            actualizaVinetaSeccionRAU_PlanoUbicacion(mxd, entidad)
        if self.parametros.Estrato == "Rural":
            entidad, extent, fc = obtieneInfoParaPlanoUbicacion(self.infoMarco.urlSecciones_Rural)
            mxd, infoMxd, escala = controlTemplates.buscaTemplatePlanoUbicacion(extent)
            actualizaVinetaSeccionRural_PlanoUbicacion(mxd, entidad)

        destacaListaPoligonos(mxd, fc)
        util.zoom(mxd, extent, escala)
        nombrePDF = generaNombrePDFPlanoUbicacion(infoMxd)

        registro = Registro(listaCodigos)
        registro.rutaPDF = generaPDF(mxd, nombrePDF, "")
        registro.formato = infoMxd['formato']
        registro.orientacion = infoMxd['orientacion']
        registro.escala = escala
        if registro.rutaPDF != "":
            registro.estado = "Plano Ubicacion"
            registro.motivo = "Croquis generado"

    def obtieneInfoParaPlanoUbicacion(self, urlServicio):
        lista = []
        try:
            condiciones = []
            for codigo in self.listaCodigos:
                condicion = "{}+%3D+{}".format(dictCamposId[parametroEstrato], codigo)
                condiciones.append(condicion)

            query = "+OR+".join(condiciones)
            url = '{}/query?token={}&where={}&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'

            fs = arcpy.FeatureSet()
            fs.load(url.format(urlServicio, self.token, query))

            fc = os.path.join("in_memory", "fc")
            fs.save(fc)

            desc = arcpy.Describe(fc)
            extent = desc.extent

            util.mensaje(extent)

            if parametroEstrato == "Manzana":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','COD_DISTRITO','COD_ZONA','COD_MANZANA','MANZENT','MANZ']
            elif parametroEstrato == "RAU":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'URBANO','CUT','EST_GEOGRAFICO','COD_CARTO','COD_SECCION','CU_SECCION']
            elif parametroEstrato == "Rural":
                fields = ['SHAPE@', 'SHAPE@AREA', 'REGION', 'PROVINCIA', 'COMUNA', 'CUT', 'COD_SECCION','COD_DISTRITO','EST_GEOGRAFICO','COD_CARTO','CU_SECCION']

            with arcpy.da.SearchCursor(fs, fields) as rows:
                lista = [r for r in rows]
            #util.mensaje(len(lista[0]))
            #extent = obtieneExtentUrbano(urlUrbano, lista[0][0], token)

            util.mensaje("** OK en obtieneInfoPara_PlanoUbicacion")
        except:
            util.mensaje("** Error en obtieneInfoPara_PlanoUbicacion")
        return lista[0], extent, fc