#!/bin/sh

echo pep8 && pep8 --ignore=W191 funyu.py && echo pyflakes && pyflakes funyu.py
echo python3 && python3 funyu.py && echo python2 && python2 funyu.py
echo coverage
coverage run funyu.py && coverage html funyu.py && google-chrome-stable htmlcov/funyu.html
