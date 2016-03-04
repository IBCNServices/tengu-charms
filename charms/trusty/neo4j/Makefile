#!/usr/bin/make
PYTHON := /usr/bin/env python

all: lint

lint:
	@flake8 --exclude hooks/charmhelpers hooks tests
	@charm proof
