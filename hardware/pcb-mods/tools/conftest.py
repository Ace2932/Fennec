# test_fab_gate.py is a standalone script (module-level sys.exit()), not a
# pytest suite -- see its own docstring and the "Script + fab-gate suites"
# step in ros-pytest.yml. Without this, `pytest hardware/pcb-mods/tools -q`
# hits it during collection and dies with INTERNALERROR> SystemExit rather
# than running the actual pytest-collectible tests in this directory (#416).
collect_ignore = ["test_fab_gate.py"]
