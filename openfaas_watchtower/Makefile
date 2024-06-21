setup:
	@poetry config virtualenvs.create true --local
	@poetry install

run: setup
	@poetry run python3 openfaas_watchtower

check_version:
	@poetry run python3 -m pytest tests