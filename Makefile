init:
	pipenv install --dev --skip-lock

format:
	pipenv run autopep8 -i --max-line-length 120 canoe/*.py tests/*.py
	pipenv run isort --skip tests/context.py canoe/*.py tests/*.py

test:
	pipenv run py.test --cov canoe tests/

.PHONY: init format test
