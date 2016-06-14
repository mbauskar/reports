import MySQLdb

def get_connection(user, host, passwd, db):
	try:
		return  MySQLdb.connect(user=user, host=host, passwd=passwd, db=db)
	except Exception, e:
		raise e

def get_values(query, db_config, as_dict=False):
	_dict_result = {}
	result = None
	_conn = get_connection(**db_config)
	try:
		_cursor = _conn.cursor()
		_cursor.execute(query)
		result = _cursor.fetchall()
		if result and as_dict:
			ret = []
			for r in result:
				row_dict = {}
				for i in range(len(r)):
					val = r[i]
					row_dict[_cursor.description[i][0]] = val
				ret.append(row_dict)

			result = ret
	except Exception, e:
		print query
		print e
		raise e
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
