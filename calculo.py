datosManzana[1] =
datosManzana2017[0] =


manzana2016 = 11638.6065209
manzana2017 =  1516.22918014

#manzana2017 = 11638.6065209
#manzana2016 =  1516.22918014
def comparaManzanas(manzana2016,manzana2017):
    if manzana2016 > manzana2017:
        print("manzana2016 > manzana2017")
        diferencia = manzana2016 -  manzana2017
        porc = diferencia/manzana2016
        print(diferencia)
    else:
        print("manzana2017 < manzana2016")
        diferencia = manzana2017 - manzana2016
        porc = diferencia/manzana2017
        print(diferencia)

    porcentaje = porc*100
    print(porcentaje)

    if porcentaje <= 5.0:
        manzana = OK
    elif porcentaje >= 6.0 and <= 40.0:
        manzana = alerta
    elif porcentaje > 40.0:
        manzana = rechazada

#a.	<= a 5% de diferencia en superficie la manzana estaría ok
#b.	>= a 6 % y <= 40% de diferencia en superficie sería alerta
#c.	> 40% de diferencia en superficie sería rechazo



comparaManzanas(11638.6065209,1516.22918014)
