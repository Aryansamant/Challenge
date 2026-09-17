.PHONY: run test ingest demo

run:
	PYTHONPATH=. python3 -m src.api.main

test:
	PYTHONPATH=. pytest -q

ingest:
	PYTHONPATH=. python3 scripts/ingest.py

demo:
	PYTHONPATH=. python3 scripts/demo.py
