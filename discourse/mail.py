def send_mail(pwd, sender="", recipients=[],  cc=[], mail_content="", subject="", file_name=None):
	import smtplib
	from email import encoders
	from email.mime.base import MIMEBase
	from email.mime.text import MIMEText
	from email.mime.multipart import MIMEMultipart
	from email.mime.application import MIMEApplication

	receivers  = []

	try:
		msg = MIMEMultipart('alternative')
		msg['Subject'] = subject
		msg['From'] = sender
		msg['To'] = ",".join("%s"%to for to in recipients)
		msg['CC'] = ",".join("%s"%to for to in cc)
		html = MIMEText(mail_content, 'html')

		# attach report
		if file_name:
			with open(file_name, "rb") as _file:
				attachment = MIMEBase("application", "octet-stream")
				attachment.set_payload(_file.read())
				# Encode the payload using Base64
				encoders.encode_base64(attachment)
				attachment.add_header(b'Content-Disposition',
					("attachment; filename=\"%s\"" % file_name.split('/')[-1]).encode('utf-8'))

		receivers = recipients + cc

		msg.attach(html)
		if file_name: msg.attach(attachment)
		
		server = smtplib.SMTP("smtp.gmail.com", 587)
		server.ehlo()
		server.starttls()
		server.login(sender, pwd)
		server.sendmail(sender, receivers, msg.as_string())
		server.close()
		return True
	except Exception, e:
		return False