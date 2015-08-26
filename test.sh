#!/bin/sh

echo pep8 && pep8 --ignore=W191 hunyu.py && echo pyflakes && pyflakes hunyu.py
echo python3 && python3 hunyu.py && echo python2 && python2 hunyu.py
echo coverage
coverage run hunyu.py && coverage html hunyu.py && google-chrome-stable htmlcov/hunyu.html
