#!/bin/sh

pep8 --ignore=W191 hunyu.py && pyflakes hunyu.py
coverage run hunyu.py && coverage html hunyu.py && google-chrome-stable htmlcov/hunyu.html
