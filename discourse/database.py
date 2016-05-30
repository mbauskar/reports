import MySQLdb

def get_connection(user, host, passwd, db):
	try:
		return  MySQLdb.connect(user=user, host=host, passwd=passwd, db=db)
	except Exception, e:
		raise e

def get_values(query, db_config):
	result = None
	_conn = get_connection(**db_config)
	try:
		_cursor = _conn.cursor()
		_cursor.execute(query)
		result = _cursor.fetchall()
	except Exception, e:
		result = None
	finally:
		return result

def set_values(query, db_config):
	result = False
	_conn = get_connection(**db_config)
	try:
		_cursor = _conn.cursor()
		_cursor.execute(query)
		_conn.commit()
		result = True
	except Exception, e:
		print query
		print e, "\n"
		_conn.rollback()
	finally:
		return result
