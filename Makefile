init:
	pipenv install --dev --skip-lock

format:
	pipenv run black .
	pipenv run isort --skip tests/context.py canoe/*.py tests/*.py

test:
	pipenv run py.test --cov canoe tests/

.PHONY: init format test
