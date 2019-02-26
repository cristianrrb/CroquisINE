define([
    "dojo/_base/declare",
    "dojo/_base/lang",
    "dojo/_base/array",
    "dojo/on",
    "dojo/Deferred",
    "dojo/request",
    "dojo/dom-construct",
    "dojo/store/Memory",
    "dijit/form/FilteringSelect",
    "jimu/BaseWidget",
    "jimu/dijit/LoadingShelter",
    "jimu/LayerStructure",
    "esri/graphicsUtils",
    "esri/symbols/SimpleFillSymbol",
    "esri/symbols/SimpleLineSymbol",
    "esri/Color",
    "esri/layers/GraphicsLayer",
    "esri/tasks/Geoprocessor",
    "esri/tasks/query"
],
function(
    declare,
    lang,
    arrayUtils,
    on,
    Deferred,
    request,
    domConstruct,
    Memory,
    FilteringSelect,
    BaseWidget,
    LoadingShelter,
    LayerStructure,
    graphicsUtils,
    SimpleFillSymbol,
    SimpleLineSymbol,
    Color,
    GraphicsLayer,
    Geoprocessor,
    Query
) {
    return declare([BaseWidget], {
        baseClass: 'jimu-widget-croquis-ine',

        postCreate: function() {
            this.inherited(arguments);
            this.shelter = new LoadingShelter({}).placeAt(this.domNode);
            this.shelter.startup();
            this.shelter.show();
        },

        startup: function () {
            if (typeof this._started === "undefined"){
                this.inherited(arguments);

                this.initConfiguracion().then(
                    lang.hitch(this, function() {
                        this.initSelectorEstrato();
                        this.initSelectorEncuesta();
                        this.initSelectorMarco();
                    })
                );

                this.identificaLayer();
                on(this.divGeneraPDF, "click", lang.hitch(this, function() {
                    this.procesaListaCodigos("", "");
                }));

                on(this.divAnalizar, "click", lang.hitch(this, function() {
                    this.procesaListaCodigos("si", "");
                }));

                on(this.divPlanoUbicacion, "click", lang.hitch(this, function() {
                    this.procesaListaCodigos("", "Si");
                }));

                this.fileReader = new FileReader();
                on(this.fileReader, "load", lang.hitch(this, function(e) {
                    if (this.tipoArchivo === "csv") {
                        this.cargaTablaCodigos(e.target.result)
                    };
                }));

                on(this.fileInput, "change", lang.hitch(this, function(evt) {
                    var f = evt.target.files[0];
                    this.tipoArchivo = "csv";
                    this.fileReader.readAsText(f);
                }))

                this.initDropZone();

                // this.simbolo = new SimpleFillSymbol(this.config.simboloArea);

                this.simbolo = new SimpleFillSymbol(SimpleFillSymbol.STYLE_SOLID,
                    new SimpleLineSymbol(SimpleLineSymbol.STYLE_SOLID,
                    new Color([98,194,204]), 2), new Color([98,194,204,0.5])
                );

                this.capaGrafica = new GraphicsLayer();
                this.map.addLayer(this.capaGrafica);

                this.shelter.hide();
                //divGeneraPDF.disabled=true;
                //divPlanoUbicacion.disabled=true;
                //divAnalizar.disabled=true;
            }
        },

        initConfiguracion: function() {
            var deferred = new Deferred();
            request(this.config.urlConfiguracion).then(
                lang.hitch(this, function(text) {
                    lang.mixin(this.config, text);
                    deferred.resolve();
                }),
                function() {
                    deferred.resolve();
                }
            );
            return deferred.promise;
        },

        initSelectorEstrato: function() {
            this.selEstrato = new FilteringSelect({
                'autoComplete': true,
                'placeHolder' : "Seleccione",
                'searchAttr': "id",
                'style': "width:100%;"
            });
            var lista = [
                {'id':"Manzana"},
                {'id':"RAU"},
                {'id':"Rural"}
            ]
            this.selEstrato.store = new Memory({'idProperty':"id", 'data':lista});
            this.selEstrato.placeAt(this.divSelectorEstrato);
            this.selEstrato.startup();
            this.selEstrato.set("value", "Manzana"); // valor inicial
        },

        initSelectorEncuesta: function() {
            this.selEncuesta = new FilteringSelect({
                'autoComplete': true,
                'placeHolder' : "Seleccione",
                'searchAttr': "id",
                'style': "width:100%;"
            });
            var lista = [
                {'id':"ENE"},
                {'id':"EPF"},
                {'id':"ENUSC"},
                {'id':"CASEN"},
                {'id':"SENDA"}
            ]
            this.selEncuesta.store = new Memory({'idProperty':"id", 'data':lista});
            this.selEncuesta.placeAt(this.divSelectorEncuesta);
            this.selEncuesta.startup();
            this.selEncuesta.set("value", "ENE"); // valor inicial
        },

        initSelectorMarco: function() {
            this.selMarco = new FilteringSelect({
                'autoComplete': true,
                'placeHolder' : "Seleccione",
                'searchAttr': "id",
                'style': "width:100%;"
            });
            var lista = [
                {'id':"2016"}
            ]
            this.selMarco.store = new Memory({'idProperty':"id", 'data':lista});
            this.selMarco.placeAt(this.divSelectorMarco);
            this.selMarco.startup();
            this.selMarco.set("value", "2016"); // valor inicial
        },

        initDropZone: function() {
            on(this.dropZone, "dragover", function(e) {
                e.stopPropagation();
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
            });
            on(this.dropZone, "drop", lang.hitch(this, function(e) {
                e.stopPropagation();
                e.preventDefault();
                var f = e.dataTransfer.files[0];
                var ext = /(?:\.([^.]+))?$/.exec(f.name)[1];
                switch(ext) {
                    case "csv":
                        this.tipoArchivo = "csv";
                        this.fileReader.readAsText(f);
                        break;
                    default:
                        this.tipoArchivo = null;
                };
            }));
        },

        cargaTablaCodigos: function(csv) {
            domConstruct.empty(this.tablaCodigos);
            domConstruct.empty(this.divDescarga);
            var lineas = csv.split("\n");
            arrayUtils.forEach(lineas, function(linea) {

                var c = linea.split(",");
                var l = c[0].trim();
                var v = ""
                if (c.length > 1) {
                    if (this.isNumeric(c[1])) {
                        v = c[1].trim();
                    }
                }

                if (this.isNumeric(l)) {
                    var tr = domConstruct.create("tr", {}, this.tablaCodigos);
                    on(tr, "click", lang.hitch(this, function(evt) {
                        evt.stopPropagation();
                        this.zoomCodigo(evt.currentTarget.codigo);
                    }));
                    domConstruct.create("td", {'class':"td-codigo",'innerHTML':l}, tr);
                    domConstruct.create("td", {'class':"td-viviendas",'innerHTML':v}, tr);
                    domConstruct.create("td", {'class':"td-estado"}, tr);

                    tr.codigo = l;
                    tr.viviendas = v
                }
            }, this);

            this.seleccionaTodo();
        },

        procesaListaCodigos: function(analizar, esPlanoUbicacion) {
            domConstruct.empty(this.divDescarga);
            // TODO: Validar duplicados
            var listaCodigos = arrayUtils.map(this.tablaCodigos.rows, function(row) {
                return row.codigo
            }, this);

            var listaTemp = arrayUtils.map(this.tablaCodigos.rows, function(row) {
                return row.viviendas
            }, this);

            var listaViviendas = arrayUtils.filter(listaTemp, function(e) {
                return e != ""
            }, this);

            this.shelter.show();
            this.generaCroquis(listaCodigos.join(","), listaViviendas.join(","), analizar, esPlanoUbicacion).then(
                lang.hitch(this, function(url) {
                    // domConstruct.create("a", {'innerHTML':"Descargar Resultado", 'href':url, 'download':"Croquis.zip", 'target':'_top'}, this.divDescarga);
                    domConstruct.create("a", {'innerHTML':"Descargar Resultado", 'href':url}, this.divDescarga);
                    this.shelter.hide();
                }),
                lang.hitch(this, function() {
                    console.log("Error");
                    this.shelter.hide();
                })
            );
        },

        generaCroquis: function(codigos, viviendas, analizar, esPlanoUbicacion) {
            var deferred = new Deferred();
            var gp = new Geoprocessor(this.config.urlServicio);
            gp.outSpatialReference = this.map.spatialReference;
            var params = {
                'Estrato':  this.selEstrato.value,
                'Encuesta': this.selEncuesta.value,
                'Marco':    this.selMarco.value,
                'Codigos':  codigos,
                'Viviendas': viviendas,
                'Analizar': analizar,
                'esPlanoUbicacion': esPlanoUbicacion
            };
            gp.setUpdateDelay(5000);
            gp.submitJob(
                params,
                lang.hitch(this, function(jobInfo) {      // Completo
                    gp.getResultData(jobInfo.jobId, "rutaRar").then(
                        lang.hitch(this, function(result) {
                            /* arrayUtils.forEach(jobInfo.messages, function(mensaje) {
                                console.log(mensaje.description);
                            }, this); */
                            deferred.resolve(result.value.url);
                        }
                    ));
                }),
                lang.hitch(this, function(jobInfo) {      // Estado
                    // console.log(jobInfo.jobStatus);
                    this.analizaMensajesGeoproceso(jobInfo);
                }),
                lang.hitch(this, function(jobInfo) {      // Error
                    console.log(jobInfo);
                    deferred.reject();
                })
            );
            return deferred.promise;
        },

        analizaMensajesGeoproceso: function(jobInfo) {
            console.log("Analizando mensajes");
            arrayUtils.forEach(jobInfo.messages, function(mensaje) {
                if (mensaje.description.substr(0, 1) == "#") {   // si comienza con #
                    var p = mensaje.description.indexOf(":", 0);
                    var codigo = mensaje.description.substring(1, p-1);

                    var contenido =  mensaje.description.substring(p+1);
                    var valores = contenido.split(",");

                    var intersectaPE = valores[0];
                    var intersectaCFT = valores[1];
                    var intersectaAV = valores[2];
                    var homologacion = valores[3];
                    var estado = valores[4];

                    this.actualizaEstadoTablaCodigos(codigo, intersectaPE, intersectaCFT, intersectaAV, homologacion, estado);
                }
            }, this);
        },

        actualizaEstadoTablaCodigos: function(codigo, intersectaPE, intersectaCFT, intersectaAV, homologacion, estado) {
            arrayUtils.forEach(this.tablaCodigos.rows, function(row) {
                if (row.cells[0].innerText == codigo) {
                    row.cells[2].innerText = estado;
                    /* if (intersecta != "") {
                        row.cells[1].innerText = intersecta
                    } */
                }
            }, this);
        },

        zoomCodigo: function(codigo) {
            if (this.selEstrato.value == "Manzana" && this.capaManzanas) {
                var query = new Query();
                query.where = "MANZENT = " + codigo;
                this.capaManzanas.queryFeatures(query, lang.hitch(this, function(result){
                    var extent = graphicsUtils.graphicsExtent(result.features);
                    this.map.setExtent(extent.expand(2),true);
                    this.map.infoWindow.setFeatures(result.features);
                }));
            }

            if (this.selEstrato.value == "RAU" && this.capaRAU) {
                var query = new Query();
                query.where = "CU_SECCION = " + codigo;
                this.capaRAU.queryFeatures(query, lang.hitch(this, function(result){
                    var extent = graphicsUtils.graphicsExtent(result.features);
                    this.map.setExtent(extent.expand(2),true);
                    this.map.infoWindow.setFeatures(result.features);
                }));
            }

            if (this.selEstrato.value == "Rural" && this.capaRural) {
                var query = new Query();
                query.where = "CU_SECCION = " + codigo;
                this.capaRural.queryFeatures(query, lang.hitch(this, function(result){
                    var extent = graphicsUtils.graphicsExtent(result.features);
                    this.map.setExtent(extent.expand(2),true);
                    this.map.infoWindow.setFeatures(result.features);
                }));
            }
        },

        seleccionaTodo: function() {
            this.capaGrafica.clear();
            if (this.selEstrato.value == "Manzana" && this.capaManzanas) {
                var query = new Query();
                query.where = this.construyeCondicionParaTodo("MANZENT");
                console.log(query.where);
                this.capaManzanas.queryFeatures(query, lang.hitch(this, function(result){
                    var extent = graphicsUtils.graphicsExtent(result.features);
                    this.map.setExtent(extent, true);
                    arrayUtils.forEach(result.features, function(feature) {
                        var graphic = feature;
                        graphic.setSymbol(symbol);
                        this.capaGrafica.add(graphic);
                    }, this);
                }));
            }
            if (this.selEstrato.value == "RAU" && this.capaRAU) {
                var query = new Query();
                query.where = this.construyeCondicionParaTodo("CU_SECCION");
                console.log(query.where);
                this.capaRAU.queryFeatures(query, lang.hitch(this, function(result){
                    var extent = graphicsUtils.graphicsExtent(result.features);
                    this.map.setExtent(extent, true);
                    arrayUtils.forEach(result.features, function(feature) {
                        var graphic = feature;
                        graphic.setSymbol(symbol);
                        this.capaGrafica.add(graphic);
                    }, this);
                }));
            }
            if (this.selEstrato.value == "Rural" && this.capaRural) {
                var query = new Query();
                query.where = this.construyeCondicionParaTodo("CU_SECCION");
                console.log(query.where);
                this.capaRural.queryFeatures(query, lang.hitch(this, function(result){
                    var extent = graphicsUtils.graphicsExtent(result.features);
                    this.map.setExtent(extent, true);
                    arrayUtils.forEach(result.features, function(feature) {
                        var graphic = feature;
                        graphic.setSymbol(symbol);
                        this.capaGrafica.add(graphic);
                    }, this);
                }));
            }
        },

        construyeCondicionParaTodo: function(campo) {
            var lista = arrayUtils.map(this.tablaCodigos.rows, function(row) {
                return campo + "=" + row.codigo
            }, this);
            return lista.join(" or ");
        },

        identificaLayer: function() {
            this.capaManzanas = null;
            this.capaRAU = null;
            this.capaRural = null;
            var layerStructure = LayerStructure.getInstance();
            layerStructure.traversal( lang.hitch(this,
                function(layerNode) {
                    if(layerNode.title == "Manzanas") {
                        this.capaManzanas = this.map.getLayer(layerNode.id);
                    };
                    if(layerNode.title == "Secciones RAU") {
                        this.capaRAU = this.map.getLayer(layerNode.id);
                    };
                    if(layerNode.title == "Secciones Rural") {
                        this.capaRural = this.map.getLayer(layerNode.id);
                    };
                })
            );
        },

        isNumeric: function(n) {
            return !isNaN(parseFloat(n)) && isFinite(n);
        }
    });
});




        /* procesaListaManzanas: function() {
            arrayUtils.forEach(this.tablaManzanas.rows, function(row) {
                var codigo = row.cells[0].innerText;
                this.imprimeManzana(codigo, row.cells[1]);
            }, this);
        }, */

        /* imprimeManzana: function(codigo, td) {
            var deferred = new Deferred();
            var gp = new Geoprocessor(this.config.urlServicio);
            gp.outSpatialReference = this.map.spatialReference;
            var params = {
                'Estrato':  this.selEstrato.value,
                'Encuesta': this.selEncuesta.value,
                'Marco':    this.selMarco.value,
                'Codigos': codigo
            };
            gp.execute(params).then(  // execute es sincronico, submitJob es asincronico
                lang.hitch(this, function(resultados) {
                    if (resultados.length > 0) {
                        url = resultados[0].value.url;
                        domConstruct.create("a", {'innerHTML':"PDF", 'href':url, 'download':"Croquis.pdf", 'target':'_top'}, td);
                        deferred.resolve();
                    } else {
                        deferred.resolve();
                    };
                }),
                lang.hitch(this, function(msg) {
                    console.log(msg);
                    td.innerHTML = "ERROR";
                    deferred.resolve([]);
                })
            );
            return deferred.promise;
        }, */
