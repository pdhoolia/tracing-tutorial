def test_imports():
    import importlib

    for mod in [
        "tracing_tutorial",
        "tracing_tutorial.tracing.backends",
        "tracing_tutorial.supervisor_demo",
    ]:
        importlib.import_module(mod)
