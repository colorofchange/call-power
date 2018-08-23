import re
from datetime import timedelta
from flask import make_response, request, current_app
from flask_jsonpify import jsonify
from functools import update_wrapper


def abortJSON(status, message=None):
    data = {'status': status.code}

    if message:
        current_app.logger.error(message)
        data['error'] = message
    else:
        data['error'] = status.name
        data['description'] = status.description
    response = jsonify(data)
    response.status_code = status.code
    return response


def stripANSI(text):
    ansi = re.compile("""
        \\x1b     # literal ESC
        \\[         # literal [
        [;\\d]*   # zero or more digits or semicolons
        [A-Za-z] # a letter
        """, re.VERBOSE)
    return ansi.sub('', text).replace('\\', '').replace('\n\n', ' ').replace('\n', '')
