.PHONY: install ingest query clean-cache help

install:
	pip install -r requirements.txt

# Run the full ingestion pipeline (discover → fetch → clean → chunk → embed)
ingest:
	python -m ingest.corpus
	python -m ingest.fetch
	python -m ingest.clean
	python -m ingest.chunk
	python -m store.embed

# Run one service at a time (useful during development)
ingest-s3:
	python -m ingest.fetch s3
	python -m ingest.clean s3
	python -m ingest.chunk s3
	python -m store.embed s3

ingest-ec2:
	python -m ingest.fetch ec2
	python -m ingest.clean ec2
	python -m ingest.chunk ec2
	python -m store.embed ec2

ingest-iam:
	python -m ingest.fetch iam
	python -m ingest.clean iam
	python -m ingest.chunk iam
	python -m store.embed iam

# Quick test query
query:
	python query.py "How do I control access to S3 buckets?"

# Wipe fetched data and Chroma DB (re-ingest from scratch)
clean-cache:
	rm -rf data/

help:
	@echo "Targets:"
	@echo "  install      Install Python dependencies"
	@echo "  ingest       Run full pipeline for all services"
	@echo "  ingest-s3    Run pipeline for S3 only"
	@echo "  ingest-ec2   Run pipeline for EC2 only"
	@echo "  ingest-iam   Run pipeline for IAM only"
	@echo "  query        Run a test query"
	@echo "  clean-cache  Delete all fetched data and the vector DB"
