"""processes the command line args.

"""

#relative import
import database as db  
import prettytable

#import from standard library
import tempfile
import re
import subprocess
from textwrap import fill
import sys
import os

###GENERAL ###



def start_process(cmd_line_args):
	"""Starts processing the command line args. Filters out unrelevant arguments.

	"""
	relevant_args = ({key: value for key, value in cmd_line_args.iteritems() 
					if value is not False and value is not None})

	if '--editor' in relevant_args:
		database = db.Database()
		database.set_editor(unicode(relevant_args['--editor'].strip(), 'utf-8'))
		print "Setting editor {0} successfull.".format(relevant_args['--editor'])
	
	elif '--suffix' in relevant_args:
		database = db.Database()	
		database.set_suffix(relevant_args['<language>'].strip(), unicode(relevant_args['--suffix'], 'utf-8'))
		print "Setting suffix {0} for {1} successfull.".format(relevant_args['--suffix'], relevant_args['<language>'])
	else:
		check_operation(relevant_args)


def split_arguments(arguments):
	"""Splits the given arguments from the command line in content and flags.

	"""
	request, flags = {}, {}
	for key, item in arguments.iteritems(): 
		if key in ('-e', '-c', '-a', '-d', '-f', '--cut', '--hline', '--suffix'):
			flags[key] = item
		else:
			request[key] = item 

	return (request, flags)


def check_operation(relevant_args):
	""" Checks which operation (add, display, ...)
		needs to be handled. 

	"""

	
	body, flags = split_arguments(relevant_args)
	database = db.Database()


	if '-f' in flags:
		process_file_adding(body)
	elif '-d' in flags:
		determine_display_operation(body, flags)
	elif '-a' in flags:
		process_add_content(body, flags)
	elif '-c' in flags:
		process_code_adding(body, database)
	else:
		print "An unexpected error has occured while processing {0} with flags {1}".format(body, flags)


def check_for_suffix(language, database):
	"""Checks if the DB has a suffix for the requested lang, if not 
	   it prompts to specify one.

	"""

	suffix = database.retrieve_suffix(language)

	if suffix:
		return suffix
	else:
		input_suffix = raw_input("Enter file suffix for language " +language+" : ").strip()
		database.set_suffix(language, input_suffix)
		return input_suffix


###OUTPUT ###

def check_for_editor(database):
	"""Checks for editor in the Database.

	"""
	editor_string = database.get_editor()
	if not editor_string:
		while True:
			try:
				editor_value = unicode(raw_input("Enter your editor: ").strip(), 'utf-8')
				break
			except UnicodeError as error:
				print error

		database.set_editor(editor_value)
		editor_string = editor_value
	else:
		editor_string = editor_string[0].encode('utf-8')
	return editor_string

def print_to_editor(table, database):
	"""Sets up a nice input form (editor) for viewing a large amount of content. -> Read only


	"""

	editor_string = check_for_editor(database)

	editor_list = [argument for argument in editor_string.split(" ")]


	initial_message = table.get_string() #prettytable to string
	with tempfile.TemporaryFile() as tmpfile:
		tmpfile.write(initial_message)
		tmpfile.flush()
		try:
	  		subprocess.Popen(editor_list + [tmpfile.name])
	  	except (OSError, IOError) as error:
	  		print "Error calling your editor - ({0}): {1}".format(error.errno, error.strerror)
	  		sys.exit(1)


def process_printing(table, results, database):
	"""Processes all priting to console or editor.

	"""
	decision = decide_where_to_print(results)
	if decision == 'console':
		print table
	else:
		print_to_editor(table, database) 


def decide_where_to_print(all_results):
	"""Decides where to print to.

	"""

	if len(all_results) < 10:
		return 'console'
	else:
		while True:
			choice = raw_input("More than 10 results - print to console anyway? (y/n)").strip().split(" ")[0]
			if choice in ('y', 'yes', 'Yes', 'Y'):
				return "console"
			elif choice in ('n', 'no', 'No', 'N'):
				return "editor"
			else:
				continue


def code_input_from_editor(suffix, database, existing_code):
	"""Sets up a nice input form (editor) for code adding and viewing.


	"""


	editor_string = check_for_editor(database)

	editor_list = [argument for argument in editor_string.split(" ")]

	initial_message = existing_code.encode('utf-8')


	with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpfile:
		if existing_code:
			tmpfile.write(initial_message)
		    	tmpfile.flush()
		file_name = tmpfile.name

		if sys.platform == "win32": #windows doing windows things
			try:
	  			subprocess.Popen(editor_list + [tmpfile.name])
	  		except (OSError, IOError) as error:
	  			print "Error calling your editor - ({0}): {1}".format(error.errno, error.strerror)
	  			sys.exit(1)
			tmpfile.close()
			while True:
			 	if raw_input("Are you done adding code? (y/n): ") != 'n':
			 		break
			 	else:
			 		continue
		else:
			try:
	  			subprocess.call(editor_list + [tmpfile.name])
	  		except (OSError, IOError) as error:
	  			print "Error calling your editor - ({0}): {1}".format(error.errno, error.strerror)
	  			sys.exit(1)

		with open(file_name) as my_file:
			try:
				file_output = my_file.read()
			except (IOError, OSError) as error:
				print error
				sys.exit(1)
			except :
				print "An unexpected error has occured."
				sys.exit(1)
		
		os.remove(file_name)
		return file_output

###CODE ###


def process_code_adding(body, database=False, target_code=False):
	"""Processes code adding, provides a nice input form for the user.

	"""

	if not database:
		database = db.Database()

	if not target_code:
		existing_code = database.retrieve_content(body, "code")
		if not existing_code:
			existing_code = ""
		else:
			existing_code = existing_code[0]
	else:
		existing_code = target_code

	suffix = check_for_suffix(body['<language>'], database)
	body['data'] = code_input_from_editor(suffix, database, existing_code)

	try:
		body['data'] = unicode(body['data'], 'utf-8')
	except UnicodeError as error:
		print error

	if body['data'] == existing_code:
		print 'Nothing changed :)'
		return False
	#update DB on change
	body['<attribute>'] = "code"

	database.upsert_code(body) 
	print "Finished - updated your codedict successfully."


###FILE ###

def process_file_adding(body):
	"""Processes adding content to DB from a file.

	"""
	
	try:
		with open(body['<path-to-file>']) as input_file:
			file_text = input_file.read()
	except (OSError, IOError) as error:
		print "File Error({0}): {1}".format(error.errno, error.strerror)
		return False

	all_matches = (re.findall(r'%.*?\|(.*?)\|[^\|%]*?\|(.*?)\|[^\|%]*\|(.*?)\|', 
		file_text, re.UNICODE))
	
		    
	database = db.Database()
 	database.add_content(all_matches, body['<language>'])
 	print "Finished - updated your codedict successfully."

	
###ADD ###

def process_add_content(body, flags):
	"""Processes content adding. 

	"""

	if '-I' in flags or '-i' in flags:
		update_content(body)
	else:
		insert_content()


def update_content(body, database=False):
	"""Processes how to update body.

	"""
	if not database:
		database = db.Database()

	if body['<attribute>'] != 'DEL': 
		while True:
			try:
				body['data'] = unicode(raw_input("Change "+body['<attribute>']+" : ").strip(), 'utf-8')
				break
			except UnicodeError as error:
				print error
		database.update_content(body)		
	else:
		database.delete_content(body)


def insert_content():
	"""Processes how to insert content.

	"""

	content_to_add = {}
	while True:
		try:
			language = unicode(raw_input("Enter language: ").strip(), 'utf-8')
			break
		except UnicodeError as error:
			print error

	for index, item in enumerate(('shortcut: ', 'command: ', 'comment: ')):
		while True:
			try: 
				content_to_add[index] = unicode(raw_input("Enter "+ item).strip(), 'utf-8') 
				break
			except UnicodeError as error:
				print error

	database = db.Database()
	database.add_content([content_to_add], language) # db function works best with lists
	print "Finished - updated your codedict successfully."


### DISPLAYING ###
 

def determine_display_operation(body, flags):
	"""Processes display actions, checks if a nice form has to be provided or not.

	"""

	cut_usecase = False
	if '--cut' in flags and '<use_case>' in body:
		cut_usecase = body['<use_case>']
	
	if '--hline' in flags:
		hline = True 
	else:
		hline = False

	database = db.Database()

	if '-e' in flags:
		if not '<use_case>' in body:
			body['<use_case>'] = ""
		results = database.retrieve_content(body, "full")
		column_list = ["Index", "use case", "command", "comment", "code added?"]
	
	elif not '<use_case>' in body:

		results = database.retrieve_content(body, "language")
		column_list = ["Index", "use case", "command", "code added?"]			
	
	else:
		results = database.retrieve_content(body, "basic")
		column_list = ["Index", "use case", "command", "code added?"]
	

	if results:
		updated_results, table = build_table(column_list, results, cut_usecase, hline)
		process_printing(table, results, database)
		process_follow_up_lookup(body, updated_results, database)
	else:
		print "No results."
		



def build_table(column_list, all_rows, cut_usecase, hline):
	"""Builds the PrettyTable and prints it to console.

	"""

	#column list length
	cl_length = len(column_list)-1
	
	result_table = prettytable.PrettyTable(column_list)
	if hline:
		result_table.hrules = prettytable.ALL 

	all_rows_as_list = []

	for row in all_rows:
		single_row = list(row)
		
		for index in range(1, cl_length - 1): # code and index dont need to be filled
			if cut_usecase and index == 1:
				single_row[index] = single_row[index].replace(cut_usecase, "", 1) 
			if not single_row[index]:
				single_row[index] = ""
			single_row[index] = fill(single_row[index], width=75/(cl_length+1))

		#if code is present, print "yes", else "no"	
		if single_row[cl_length]:
			single_row[cl_length] = "yes"
		else:
			single_row[cl_length] = "no" 

		#add modified row to table, add original row to return-list
		result_table.add_row(single_row)
		all_rows_as_list.append(list(row))

	return (all_rows_as_list, result_table)


###SECOND ###

def prompt_by_index(results):
	"""Prompts the user for further commands after displaying content.
	   Valid input: <index> [attribute] 
	"""

	valid_input = False 

	while not valid_input:

		user_input = (raw_input(
		"Do you want to do further operations on the results? (CTRL-C to abort): ")
		.strip().split(None, 1))
		
		index = user_input[0]
		try:
			attribute = user_input[1]
		except IndexError:
			attribute = ""

		if len(user_input) <= 2 and index.isdigit() and int(index) >= 1 and int(index) <= len(results):	
			actual_index = int(index)-1
			valid_input = True
			if attribute: 
				if not attribute in ('use_case', 'command', 'comment', 'DEL'):
					print "Wrong attribute, Please try again."
					valid_input = False
		else:
			print "Wrong index, Please try again."
	return (results[actual_index], attribute) 		


def process_follow_up_lookup(original_body, results, database):
	"""Processes the 2nd operation of the user, e.g. code adding.

	"""

	target, attribute = prompt_by_index(results)

	if '<use_case>' in original_body:
		original_body['<use_case>'] = target[1]
	
	if attribute:
		original_body['<attribute>'] = attribute
		return update_content(original_body, database=database)
	else:
		target_code = target[len(target)-1]
		if not target_code:
			target_code = " "
		return process_code_adding(original_body, target_code=target_code, database=database)

