import sys
import json
import requests
from datetime import datetime
from jinja2 import Environment, PackageLoader
from database import get_values, set_values	


jenv = None
users = {}
base_url = ""
activity_url = ""
topic_url = "{base_url}/t/{slug}"
db_config = {}

def init_report():
	global jenv, users, base_url, activity_url, db_config

	jenv = Environment(loader=PackageLoader("user_activity", 'templates'))
	config = {}

	with open("config.json", "r") as file:
		config = file.read()
		config = json.loads(config) if config else {}

	if not config:
		return

	users = config.get("users", [])
	base_url = config.get("base_url", "")
	activity_url = config.get("activity_url", "")
	db_config = config.get("db_config", {})
	
	get_users_activity_records(base_url, users.keys())

def format_date(str_datetime=None):
	date = None
	date = datetime.now() if not str_datetime else datetime.strptime(str_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
	return date.strftime("%Y-%m-%d")

def get_user_actions(url):
	response = requests.get(url)
	if response.ok and response.status_code == 200:
		actions = response.json()
		return actions.get("user_actions", []) if isinstance(actions, dict) else []
	else:
		raise Exception("Error while fetching Users activity")

def prepare_actions(user, actions):
	# prepare activities according to Topic
	def get_action(operation):
		operations = {
			"closed.enabled": "Closed the Topic"
		}

		return operations.get(operation) or "Unknown Action"

	report = {}
	for action in actions:
		if user not in [action.get("acting_username"), action.get("username")]:
			continue

		if format_date(action.get("created_at")) != format_date():
			continue

		key = action.get("slug")
		activity = {
			"title": action.get("title"),
			"post_number": action.get("post_number"),
			"created_at": format_date(action.get("created_at")),
			"action": action.get("excerpt") if action.get("excerpt") else get_action(action.get("action_code")),
			"topic_id": action.get("topic_id")
		}

		activities = report.get(key) or []
		activities.append(activity)

		report.update({
			key: activities
		})

	return report

def to_html(user, activity_report):
	from operator import itemgetter
	for_pdf = for_mail = ""
	if not activity_report:
		return [None, None]

	for_mail = jenv.get_template("user_mail_report_summary.html").render({
					"base_url": base_url,
					"user": users.get(user),
					"topics": activity_report
				})

	return ["", for_mail]

def get_parent(slug):
	query = """ select id from `Topics` where slug='%s' """%slug

	result = get_values(query, db_config)
	if not result:
		query = """ insert into `Topics` (slug) values ('%s') """%slug
		if set_values(query, db_config):
			return get_parent(slug)
	else:
		return result[0][0]

def save_activity_report_to_db(user, activity_report):
	def is_saved(parent, user, action):
		return False

	def add_activity(parent, user, action):
		# check if activity already exists
		if not is_saved(parent, user, action):
			query = """ 
						insert into `UserActivity` (parent, created_at, user, topic_id,
						post_number, title) values (%s,'%s', '%s','%s',%s,'%s')
					"""%(	
							parent,
							action.get('created_at'),
							user,
							action.get('topic_id'),
							action.get('post_number'),
							action.get('title'),
						)
			set_values(query, db_config)

	if not activity_report:
		return

	for slug, actions in activity_report.iteritems():
		parent = get_parent(slug)
		[add_activity(parent, user, action) for action in actions]

def get_users_activity_records(base_url, users):
	if not users:
		return None

	user_reports = {}
	user_wise_summary = []
	for user in users:
		try:
			url = activity_url.format(base_url=base_url, username=user)
			actions = get_user_actions(url)
			if not actions:
				continue			

			activity_report = prepare_actions(user, actions)
			save_activity_report_to_db(user, activity_report)

			pdf_report_html, mail_report_html = to_html(user, activity_report)

			if mail_report_html: user_wise_summary.append(mail_report_html)
			# user_reports.update({
			# 	user:{
			# 		"pdf_report_html": pdf_report_html or "No Activity",
			# 		"mail_report_html": mail_report_html or "No Activity"
			# 	}
			# })
		except Exception, e:
			import traceback
			print e
			print traceback.print_exc()

	mail_content = jenv.get_template("mail_template.html").render({
						"user_wise_summary": user_wise_summary
					})

	# with open("report.html", "w+") as file:
	# 	file.write(mail_content)

if __name__ == "__main__":
	init_report()