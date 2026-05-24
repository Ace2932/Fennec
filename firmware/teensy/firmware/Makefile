# Teensy 4.1 firmware build + deploy.
#
# Per docs/notes-qol-features.md §5: build on the laptop, flash over the
# Jetson's USB connection to the Teensy. No need to pull the Teensy
# out of the chassis.
#
# Configure via env (or override on the command line):
#   JETSON_HOST       SSH target (default: aiden@nova-jetson.local)
#   TEENSY_MCU        teensy_loader_cli model (default: TEENSY41)
#   PIO_ENV           PlatformIO env (default: teensy41)
#   HASH_CACHE        local hash record (default: ~/.nova/last-deployed.sha)
#
# Usage:
#   make build        # local pio build
#   make deploy       # build, hash-check, scp, remote flash, verify
#   make deploy-force # skip hash-check (always flash)
#   make verify       # check /firmware_version on Jetson matches deploy

JETSON_HOST ?= aiden@nova-jetson.local
TEENSY_MCU  ?= TEENSY41
PIO_ENV     ?= teensy41
HEX_PATH    := .pio/build/$(PIO_ENV)/firmware.hex
SCRIPTS_DIR := ../../../scripts
DEPLOY_SH   := $(SCRIPTS_DIR)/deploy-firmware.sh

.PHONY: build deploy deploy-force verify clean help

help:
	@echo 'Targets:'
	@echo '  build         pio run -e $(PIO_ENV)'
	@echo '  deploy        build + hash-check + scp + remote flash + verify'
	@echo '  deploy-force  skip hash-check'
	@echo '  verify        echo /firmware_version on the Jetson'
	@echo '  clean         pio run -t clean'

build:
	pio run -e $(PIO_ENV)

deploy: build
	JETSON_HOST=$(JETSON_HOST) TEENSY_MCU=$(TEENSY_MCU) \
		HEX_PATH=$(HEX_PATH) \
		$(DEPLOY_SH)

deploy-force: build
	JETSON_HOST=$(JETSON_HOST) TEENSY_MCU=$(TEENSY_MCU) \
		HEX_PATH=$(HEX_PATH) DEPLOY_FORCE=1 \
		$(DEPLOY_SH)

verify:
	JETSON_HOST=$(JETSON_HOST) $(DEPLOY_SH) verify

clean:
	pio run -t clean
