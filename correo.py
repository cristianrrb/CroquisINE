fromaddrMail = "marcelojimenez9@gmail.com"
toaddrsMail  = "mjimenez@esri.cl"
usernameMail = "marcelojimenez9@gmail.com"
passwordMail = ""

import smtplib

def enviarCorreo():
	fromaddr = fromaddrMail
	toaddrs  = toaddrsMail

	msg = ("ENVIANDO CORREO ELECTRONICO ")

	username = usernameMail
	password = passwordMail

	# Enviando el correo
	server = smtplib.SMTP('smtp.gmail.com:587')
	server.starttls()
	server.login(username,password)
	server.sendmail(fromaddr, toaddrs, msg)
	server.quit()
----------------------------------------------------------------------

fromaddrMail = "marcelojimenez9@gmail.com"
toaddrsMail  = "marcelojimenez9@gmail.com"
usernameMail = "marcelojimenez9@gmail.com"
passwordMail = "clave"

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from email.mime.text import MIMEText
from smtplib import SMTP
def main():
    from_address = fromaddrMail
    to_address = toaddrsMail
    message = "Hello, world!"

    mime_message = MIMEText(message, "plain")
    mime_message["From"] = from_address
    mime_message["To"] = to_address
    mime_message["Subject"] = "Correo de prueba"

    smtp = SMTP('smtp.gmail.com', 587)
    smtp.login(from_address, passwordMail)

    smtp.sendmail(from_address, to_address, mime_message.as_string())
    smtp.quit()
if __name__ == "__main__":
    main()


--------------------------

import email
import smtplib

msg = email.message_from_string("warning")
msg["From"] = "marcelojimenez9@gmail.com"
msg["To"] = "marcelojimenez9@gmail.com"
msg["Subject"] = "helOoooOo"

s = smtplib.SMTP("smtp.live.com",587)
s.ehlo() # Hostname to send for this command defaults to the fully qualified domain name of the local host.
s.starttls() #Puts connection to SMTP server in TLS mode
s.ehlo()
s.login("marcelojimenez9@gmail.com", "Titito.05052017")

s.sendmail("marcelojimenez9@gmail.com", "marcelojimenez9@gmail.com", msg.as_string())

s.quit()

-------------------------------------------------------------------------------------------
FUNKAAAAAAAA

import smtplib

mailserver = smtplib.SMTP('smtp.office365.com',587)
mailserver.ehlo()
mailserver.starttls()
mailserver.login('mjimenez@esri.cl', 'Marce6550esRi')
mailserver.sendmail('mjimenez@esri.cl','marcelojimenez9@gmail.com','PRUEBAAAAAAAAAA')
mailserver.quit()

---------------------------------------------------------------------------------------------


import smtplib
import base64

sendto = 'marcelojimenez9@gmail.com'
user= 'mjimenez@esri.cl'
password = base64.b64encode("Marce6550esRi")
smtpserver = smtplib.SMTP('smtp.office365.com',587)

smtpserver.ehlo()
smtpserver.starttls()
smtpserver.ehlo
smtpserver.login(user, password)
header = 'To:' + sendto + 'n' + 'From: ' + user + 'n' + 'Subject:testing n'
print header
msgbody = header + 'n This is a test Email send using Python nn'
smtpserver.sendmail(user, sendto, msgbody)
print 'done!'
smtpserver.close()
