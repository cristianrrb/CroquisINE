# -*- coding: iso-8859-1 -*-
import arcpy
import os
from util import mensaje

class Templates:

    def __init__(self, config, parametros):
        self.config = config

    def listaMXDs(self, estrato, ancho):
        d = {"Manzana": 0, "RAU": 1, "Rural": 2}
        lista = []
        for e in self.config['estratos']:
            if e['nombre'] == estrato:
                if ancho:
                    lista = [m for m in self.config['estratos'][d[estrato]]['mxds'] if m['ancho'] > m['alto']]
                else:
                    lista = [m for m in self.config['estratos'][d[estrato]]['mxds'] if m['ancho'] <= m['alto']]
        return lista

    def listaMXDsPlanoUbicacion(self, estrato, ancho):
        d = {"Manzana":0,"RAU":1,"Rural":2}
        lista = []
        for e in self.config['estratos']:
            if e['nombre'] == estrato:
                if ancho:
                    lista = [m for m in self.config['estratos'][d[estrato]]['mxdsPlanoUbicacion'] if m['ancho'] > m['alto']]
                else:
                    lista = [m for m in self.config['estratos'][d[estrato]]['mxdsPlanoUbicacion'] if m['ancho'] <= m['alto']]
        return lista

    def mejorEscalaMXD(self, mxd, alto, ancho):
        #5 a 1000x100 (500 a 100000)
        escalas = [e for e in range(5, 10000)]
        for e in escalas:
            if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
                return e * 100
        return None

    def mejorEscalaMXDManzana(self, mxd, alto, ancho):
        #5 a 35x100 (500 a 3500)
        escalas = [e for e in range(5, 36)]
        for e in escalas:
            if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
                return e * 100
        return None

    def mejorEscalaMXDRAU(self, mxd, alto, ancho):
        #5 a 76x100 (500 a 7500)
        escalas = [e for e in range(5, 76)]
        for e in escalas:
            if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
                return e * 100
        return None

    def mejorEscalaMXDRural(self, mxd, alto, ancho):
        #5 a 200x100 (500 a 2000)
        escalas = [e for e in range(5, 210)]
        for e in escalas:
            if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
                return e * 100
        return None

    def mejorEscalaMXDPlanoUbicacion(self, mxd, alto, ancho):
        # Plano Ubicación A0 1: 7.500
        escalas = [e for e in range(5, 76)]
        for e in escalas:
            if (ancho < (mxd['ancho'] * e)) and (alto < (mxd['alto'] * e)):
                return e * 100
        return None

    def buscaTemplateManzana(self, extent):
        try:
            ancho = extent.XMax - extent.XMin
            alto = extent.YMax - extent.YMin
            lista = self.listaMXDs("Manzana", (ancho > alto))
            for infoMxd in lista:
                escala = self.mejorEscalaMXDManzana(infoMxd, alto, ancho)
                if escala != None:
                    rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                    #util.mensaje("1")
                    mxd = arcpy.mapping.MapDocument(rutaMXD)
                    # util.mensaje('Se selecciono layout para manzana.')
                    return mxd, infoMxd, escala
        except:
            pass
        # util.mensaje('** Error: No se selecciono layout para manzana.')
        return None, None, None

    def buscaTemplateRAU(self, extent):
        try:
            #util.mensaje("funcion buscaTemplateRAU")
            ancho = extent.XMax - extent.XMin
            alto = extent.YMax - extent.YMin
            lista = self.listaMXDs("RAU", (ancho > alto))
            for infoMxd in lista:
                escala = self.mejorEscalaMXDRAU(infoMxd, alto, ancho)
                if escala != None:
                    rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                    mxd = arcpy.mapping.MapDocument(rutaMXD)
                    #util.mensaje('Se seleccionó layout para RAU.')
                    #util.mensaje("infoMxd = {}".format(infoMxd))
                    #util.mensaje("escala = {}".format(escala))
                    return mxd, infoMxd, escala

            # si no se ajusta dentro de las escalas limites se usa el papel más grande sin limite de escala
            escala = self.mejorEscalaMXD(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                #util.mensaje('Se seleccionó layout para RAU.(Excede escala)')
                #util.mensaje("infoMxd = {}".format(infoMxd))
                #util.mensaje("escala = {}".format(escala))
                return mxd, infoMxd, escala
        except:
            pass
        #util.mensaje('** Error: No se selecciono layout para RAU. (Excede escala)')
        return None, None, None

    def buscaTemplateRural(self, extent):
        try:
            ancho = extent.XMax - extent.XMin
            alto = extent.YMax - extent.YMin
            lista = self.listaMXDs("Rural", (ancho > alto))
            for infoMxd in lista:
                escala = self.mejorEscalaMXDRural(infoMxd, alto, ancho)
                if escala != None:
                    rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                    mxd = arcpy.mapping.MapDocument(rutaMXD)
                    #util.mensaje('Se selecciono layout para Rural.')
                    return mxd, infoMxd, escala

            # si no se ajusta dentro de las escalas limites se usa el papel más grande sin limite de escala
            escala = self.mejorEscalaMXD(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                #util.mensaje('Se selecciono layout para Rural. (Excede escala)')
                return mxd, infoMxd, escala
        except:
            pass
        #util.mensaje('** Error: No se selecciono layout para Rural.')
        return None, None, None

    def buscaTemplatePlanoUbicacion(self, estrato, extent):
        try:
            ancho = extent.XMax - extent.XMin
            alto = extent.YMax - extent.YMin
            lista = self.listaMXDsPlanoUbicacion(estrato, (ancho > alto))
            for infoMxd in lista:
                escala = self.mejorEscalaMXDPlanoUbicacion(infoMxd, alto, ancho)
                if escala != None:
                    rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                    mxd = arcpy.mapping.MapDocument(rutaMXD)
                    mensaje('Se selecciono layout para Plano Ubicacion.')
                    return mxd, infoMxd, escala

            # si no se ajusta dentro de las escalas limites se usa el papel más grande sin limite de escala
            escala = mejorEscalaMXD(infoMxd, alto, ancho)
            if escala != None:
                rutaMXD = os.path.join(self.config['rutabase'], 'MXD', infoMxd['ruta'] + ".mxd")
                mxd = arcpy.mapping.MapDocument(rutaMXD)
                util.mensaje('Se selecciono layout para Plano Ubicacion (Excede escala)')
                util.mensaje("infoMxd = {}".format(infoMxd))
                util.mensaje("escala = {}".format(escala))
                return mxd, infoMxd, escala
        except:
            pass
        util.mensaje('** Error: No se selecciono layout para Plano Ubicacion.')
        return None, None, None
