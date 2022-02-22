.PHONY: install start test

install:
	python -m pip install -e .

up:
	python -m kwik

test:
	pytest test/
