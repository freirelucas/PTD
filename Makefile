.PHONY: build test commit clean help

help:
	@echo "Targets:"
	@echo "  make build   - reconstrói ptd_scraper.ipynb a partir de notebook_cells/"
	@echo "  make test    - roda pytest sobre tests/"
	@echo "  make commit  - build + git add -A + git commit"
	@echo "  make clean   - remove artefatos de execução local (ptd_output/)"

build:
	python build_notebook.py

test:
	python -m pytest -v tests/

commit: build
	git add -A
	git commit

clean:
	rm -rf ptd_output/
