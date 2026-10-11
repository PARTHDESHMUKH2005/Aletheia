.PHONY: build-ApiFunction build-PipelineFunction

# Package application code only: .env, tests and local uploads stay out of Lambda.
build-ApiFunction build-PipelineFunction:
	python -m pip install -r requirements.txt --target "$(ARTIFACTS_DIR)"
	python -c 'import shutil,sys; shutil.copytree("app", sys.argv[1]+"/app", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))' "$(ARTIFACTS_DIR)"
