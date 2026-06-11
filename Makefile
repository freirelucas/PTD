.PHONY: build metadata corpus corpus-zip test smoke commit clean help

help:
	@echo "Targets:"
	@echo "  make build      - reconstrói ptd_scraper.ipynb a partir de notebook_cells/"
	@echo "  make metadata   - (re)gera os descritores de dados abertos em output/"
	@echo "  make corpus     - (re)gera o corpus harmonizado em output/harmonized/"
	@echo "  make corpus-zip - empacota só o corpus (harmonized/ + manifest) em corpus_<snapshot>.zip"
	@echo "  make test       - roda pytest sobre tests/"
	@echo "  make smoke      - smoke test do notebook (sintaxe, deps, carga; --live p/ scraper)"
	@echo "  make commit     - build + git add -A + git commit"
	@echo "  make clean      - remove artefatos de execução local (ptd_output/)"

build:
	python build_notebook.py

metadata:
	python build_metadata.py

corpus:
	python build_corpus.py

corpus-zip:
	python build_corpus.py --zip

test:
	python -m pytest -v tests/

smoke:
	python smoke_test.py

commit: build
	git add -A
	git commit

clean:
	rm -rf ptd_output/
