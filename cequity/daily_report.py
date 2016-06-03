import os
import sys
import json
import requests
from mail import send_mail
from database import get_values, set_values	
# from jinja2 import Environment, PackageLoader
from datetime import datetime, date, timedelta

cc = []
sender = []
db_config = {}
recipients = []
report_path = {}
report_names = {}
mail_subject = {}
daily_reports = []
weekly_reports = []
report_headers = {}
filename_formats = {}
date_format = "%Y-%m_%d"

def init_report(mail_pwd):
	global sender, db_config, recipients, report_path, mail_subject, \
		daily_reports, weekly_reports, filename_formats, date_format, \
		report_headers, cc, report_names

	# get config from db config

	with open("./config.json", "r") as file:
		config = json.loads(file.read())
		if not config:
			raise Exception("config not found")
		
		cc = config.get("cc")
		sender = config.get("sender")
		db_config = config.get("db_config")
		recipients = config.get("recipients")
		notify_user = config.get("notify_user")
		date_format = config.get("date_format")
		report_path = config.get("report_path")
		report_names = config.get("report_names")
		mail_subject = config.get("mail_subject")
		daily_reports = config.get("daily_reports")
		weekly_reports = config.get("weekly_reports")
		report_headers = config.get("report_headers")
		filename_formats = config.get("filename_formats")

	reports = get_report_names()
	queries = get_queries(reports)
	results = fetch_and_save_reports(reports, queries)
	print results
	# if notify_user: send_notification_mail(results)
	send_notification_mail(mail_pwd, results)

def get_report_date(date_format="%Y-%m-%d", str_datetime=None, as_string=True, days=1):
	date = None
	date = datetime.now() if not str_datetime else datetime.strptime(str_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
	date = date - timedelta(days=days)
	return date.strftime(date_format) if as_string else date

def get_report_names():
	reports = []
	reports = daily_reports + weekly_reports if get_report_date(date_format="%a") == "Mon" else daily_reports
	return reports

def get_queries(reports):
	queries = {}
	for report in reports:
		query_fname = "./queries/{report}.sql".format(report=report)
		with open(query_fname, "r") as file:
			query = file.read().replace("\n", " ")
			queries.update({ report: query or "" })
	return queries

def fetch_and_save_reports(reports, queries):
	results = []
	start = None
	total_records = 0

	report_date = get_report_date()
	for report in reports:
		try:
			start = get_report_date(date_format="%H:%M:%S", days=0)

			query = queries.get(report)
			query = query.format(report_date=report_date)
			
			# data = get_values(query, db_config)
			data = []
			content = prepare_csv_data(report, data)
			save_csv_report(report, content, report_date)

			total_records = len(data)
			results.append({
				"report": report_names.get(report),
				"is_sucessful": True,
				"start": start,
				"end": get_report_date(date_format="%H:%M:%S", days=0),
				"total_records": total_records,
				"result": "CSV Created"
			});
		except Exception, e:
			results.append({
				"report": report_names.get(report),
				"is_sucessful": False,
				"start": start or "",
				"end": get_report_date(date_format="%H:%M:%S", days=0),
				"total_records": total_records,
				"result": "Error while creating CSV"
			});
	return results

def prepare_csv_data(report, data):
	content = []
	header = "|".join(report_headers.get(report))
	
	if not data:
		content = [header]
	else:
		content.append(header)
		content.extend(["|".join(row) for row in data])
	return content

def create_directory(base_path, dir_name=None):
	if not base_path and not dir_name:
		raise Exception("Report Path and Directory name not provided")
	if not os.path.isdir(base_path):
		raise Exception("Report Path does not exists")

	dir_path = "{base_path}/{dir_name}".format(base_path=base_path, dir_name=dir_name)
	if not os.path.isdir(dir_path):
		os.makedirs(dir_path)

def save_csv_report(report, content, report_date):
	filename = filename_formats.get(report)
	filename = filename.format(report_date=report_date)
	create_directory(report_path, dir_name=report_date)
	file_path = "{report_path}/{report_date}/{filename}".format(
		report_path=report_path,
		report_date=report_date,
		filename=filename
	)

	with open(file_path, "w") as file:
		file.writelines(content)

def send_notification_mail(mail_pwd, results):
	mail_template = ""
	report_result_template = ""
	report_result = ""
	# get template

	with open("./templates/mail_template.html", "r") as file:
		mail_template = file.read()

	with open("./templates/report_result.html", "r") as file:
		report_result_template = file.read()

	for report in results:
		report_result += report_result_template.format(**report)

	mail_content = mail_template.format(
		report_result=report_result,
		report_path=report_path
	)
	send_mail(mail_pwd, recipients=recipients, sender=sender, 
		subject=mail_subject, mail_content=mail_content, cc=cc)

if __name__ == "__main__":
	try:
		if len(sys.argv) == 2:
			init_report(sys.argv[1])
		else:
			print "missing parameter"
	except Exception, e:
		import traceback
		print e
		print traceback.print_exc()