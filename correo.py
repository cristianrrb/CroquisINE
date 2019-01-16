fromaddrMail = "marcelojimenez9@gmail.com"
toaddrsMail  = "marcelojimenez9@gmail.com"
usernameMail = "marcelojimenez9@gmail.com"
passwordMail = "clave"

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
