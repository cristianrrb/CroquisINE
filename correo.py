import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

fromMail = "mjimenez@esri.cl"
passwordFromMail = 'Marce6550esRi'
#
#fromMail = "marcelojimenez9@gmail.com"
#passwordFromMail = "Titito.05052017"
#fromMail = "sig@ine.cl"
#passwordFromMail = "(ine2018)"
toMail = "marcelojimenez9@gmail.com"
#toMail = "mjimenez@esri.cl"

# Create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = "Reporte Croquis INE Nro: "
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
<p>Reporte croquis de alertas y rechazo para Instituto Nacional de Estadísticas de Chile</p>
<u>Motivos de Rechazo y/o Alertas:</u>
<ul>
    <li type="disc">Rechazo, Manzana con menos de 8 viviendas; Cuando 'Motivo Rechazo' es, Rechazado.</li>
    <li type="disc">Alerta, Manzana Intersecta con Permiso de Edificación (PE); Cuando 'Intersecta PE' es, Si.</li>
    <li type="disc">Alerta, Manzana Intersecta con Certificado de Recepción Final (CRF); Cuando 'Intersecta CRF' es, Si.</li>
    <li type="disc">Alerta, Manzana Intersecta con Áreas Verdes (AV); Cuando 'Intersecta AV' es, Si.</li>
    <li type="disc">Alerta, Manzana Homologación No es Idéntica; cuando 'Homologación' es, Homologada No Idéntica</li>
    <li type="disc">Alerta, Estado es 'No generado' cuando no se pudo generar el croquis.</li>
</ul>
</br>
<p><b>Departamento de Geografía</b></p>
<p>Instituto Nacional de Estadísticas</p>
<p>Fono: 232461860</p>
</body>
</html>
"""

part1 = MIMEText(html, 'html')
msg.attach(part1)
#mailserver = smtplib.SMTP('smtp.office365.com',587)
mailserver = smtplib.SMTP('smtp.gmail.com',587)
mailserver.ehlo()
mailserver.starttls()
mailserver.login(fromMail, passwordFromMail)
mailserver.sendmail(fromMail, toMail, msg.as_string())
mensaje("Reporte Enviado")
mailserver.quit()
