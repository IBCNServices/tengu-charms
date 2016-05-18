# Copyright (C) 2016  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Helper module for pretty console output"""
#pylint: disable=c0111
import smtplib
import socket

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

def debug(text):
    print 'DEBUG: {}'.format(text)

def okblue(text):
    print OKBLUE + str(text) + ENDC

def okgreen(text):
    print OKGREEN + str(text) + ENDC

def okwhite(text):
    print str(text)

def warn(text):
    print OKGREEN + str(text) + ENDC

def fail(reason, exception=None):
    if exception:
        print str(exception)
    print '{}ERROR: {}{}'.format(FAIL, reason, ENDC)
    exit(1)

def mail(text):
    FROM = "{}@{}".format('Hauchiwa', socket.gethostname())
    TO = ["merlijn.sebrechts@gmail.com"] # must be a list
    SUBJECT = "Warning from {}".format(FROM)
    TEXT = text
    # Prepare actual message
    message = """\
    From: {}
    To: {}
    Subject: {}
    {}
    """.format(FROM, ", ".join(TO), SUBJECT, TEXT)
    # Send the mail
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login('tengu.butler@gmail.com','123your_password')
    server.sendmail(FROM, TO, message)
    server.quit()
