import sys
import json
import requests
from mail import send_mail
from database import get_values, set_values	
from jinja2 import Environment, PackageLoader
from datetime import datetime, date, timedelta

jenv = None
users = {}
sender = ""
subject = ""
mail_pwd = ""
base_url = ""
db_config = {}
topic_url = "{base_url}/t/{slug}"
recipients = []
activity_url = ""
keep_active_user_in_cc = False

def init_report(pwd):
	global jenv, users, base_url, activity_url, db_config, recipients, subject, sender, mail_pwd

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
	recipients = config.get("recipients", [])
	subject = config.get("mail_subject", {})
	sender = config.get("sender", {})
	keep_active_user_in_cc = config.get("keep_active_user_in_cc", False)
	mail_pwd = pwd
	
	get_users_activity_records(base_url, users.keys())

def format_date(date_format='%Y-%m-%d', str_datetime=None, as_string=True, days=1):
	date = None
	date = datetime.now() if not str_datetime else datetime.strptime(str_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
	date = date - timedelta(days=days)
	return date.strftime(date_format) if as_string else date

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

		if format_date(str_datetime=action.get("created_at"), days=0) != format_date():
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
		query = """ select id from `UserActivity` where user='%s' and topic_id='%s'
					and post_number=%s"""%(user, action.get("topic_id"), action.get("post_number"))
		if get_values(query, db_config):
			return True
		else:
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

def get_activity_summery():
	records = {}

	def prepare_activity(result):
		return {
			slug: [{
				"post_number": result.get("post_number"),
				"created_at": result.get("created_at"),
				"topic_id": result.get("topic_id"),
				"title": result.get("title")
			}]
		}


	query = """ select ua.*, t.slug from `UserActivity` ua inner join `Topics` t on t.id=ua.parent
				where (created_at between "{start_date}" and "{end_date}")""".format(
					start_date=format_date(days=7),
					end_date=format_date(days=1)
				)
	results = get_values(query, db_config, as_dict=True)
	if not results:
		return {}

	for result in results:
		user = result.get("user")
		slug = result.get("slug")

		record = records.get(user, {})
		if not record:
			activity = prepare_activity(result)
		elif record and not record.get(slug, {}):
			current_activity = prepare_activity(result)
			activity = records.get(user, {})
			activity.update(current_activity)
		else:
			activity = records.get(user)
			current_activity = prepare_activity(result)
			old_activity = record.get(slug, [])
			old_activity.extend(current_activity.get(slug))
			activity.update({ slug: old_activity })

		records.update({ user: activity })
	return records

def get_total_reply_count():
	totals = {}
	query = """ select user, count(id) as total from UserActivity where 
				(created_at between "{start_date}" and "{end_date}") group by user""".format(
					start_date=format_date(days=7),
					end_date=format_date(days=1)
				)
	results = get_values(query, db_config, as_dict=True)
	for result in results:
		totals.update({ result.get("user"): result.get("total") })
	return totals

def mail_activity_report(user_wise_summary):

	mail_content = jenv.get_template("mail_template.html").render({
						"base_url": base_url,
						"user_wise_summary": user_wise_summary,
						"users": users,
						"from_date": format_date(days=7),
						"to_date": format_date(days=1),
						"totals": get_total_reply_count()
					})
	mail_subject = subject.format(
		from_date=format_date(date_format="%d-%b-%y", days=7),
		to_date=format_date(date_format="%d-%b-%y", days=1)
	)

	if keep_active_user_in_cc:
		active_users = [users.get(user).get("email") for user in user_wise_summary.keys()]

	send_mail(mail_pwd, recipients=recipients, sender=sender, 
		subject=mail_subject, mail_content=mail_content, cc=active_users)

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

		except Exception, e:
			import traceback
			print e
			print traceback.print_exc()

	try:
		if format_date(date_format="%a") == "Sun":
			print "sending mail"
			user_wise_summary = get_activity_summery()
			mail_activity_report(user_wise_summary)
	except Exception, e:
		raise e

if __name__ == "__main__":
	if len(sys.argv) == 2:
		init_report(sys.argv[1])
	else:
		print "missing parameter"