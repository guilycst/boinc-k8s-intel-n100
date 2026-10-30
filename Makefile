PYTHON ?= python3

.PHONY: check image
check:
	$(PYTHON) runtime/cpu-guard.py --self-test
	$(PYTHON) runtime/gpu-guard.py --self-test
	$(PYTHON) -m unittest discover -s runtime -p 'test_*.py'
	$(PYTHON) tests/validate.py

image:
	docker build --platform linux/amd64 -t boinc-k8s-intel-n100:local image
