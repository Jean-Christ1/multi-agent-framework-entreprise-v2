import pytest

from framework.engine.factory import EngineFactory


class DummyActor:
    def __init__(self, llm_config=None):
        self.llm_config = llm_config


def test_factory_all_llm_none_selects_native(monkeypatch, caplog):
    import framework.engine.factory as factory_module

    caplog.set_level("INFO", logger="framework.engine.factory")

    seen = []

    def fake_create_engine(engine_type: str, **kwargs):
        seen.append(engine_type)
        return ("engine", engine_type)

    monkeypatch.setattr(factory_module, "create_engine", fake_create_engine)

    actors = [DummyActor(llm_config=None), DummyActor(llm_config=None)]
    engine = EngineFactory.create(actors)

    assert engine == ("engine", "native")
    assert seen == ["native"]
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


def test_factory_any_llm_set_selects_crewai(monkeypatch, caplog):
    import framework.engine.factory as factory_module

    caplog.set_level("INFO", logger="framework.engine.factory")

    seen = []

    def fake_create_engine(engine_type: str, **kwargs):
        seen.append(engine_type)
        return ("engine", engine_type)

    monkeypatch.setattr(factory_module, "create_engine", fake_create_engine)

    actors = [DummyActor(llm_config=None), DummyActor(llm_config={"model": "gpt"})]
    engine = EngineFactory.create(actors)

    assert engine == ("engine", "crewai")
    assert seen == ["crewai"]
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


def test_factory_mixed_actors_selects_crewai(monkeypatch, caplog):
    import framework.engine.factory as factory_module

    caplog.set_level("INFO", logger="framework.engine.factory")

    seen = []

    def fake_create_engine(engine_type: str, **kwargs):
        seen.append(engine_type)
        return ("engine", engine_type)

    monkeypatch.setattr(factory_module, "create_engine", fake_create_engine)

    actors = [DummyActor(llm_config={"model": "gpt"}), DummyActor(llm_config=None)]
    engine = EngineFactory.create(actors)

    assert engine == ("engine", "crewai")
    assert seen == ["crewai"]
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


def test_factory_forced_native_overrides_auto(monkeypatch, caplog):
    import framework.engine.factory as factory_module

    caplog.set_level("INFO", logger="framework.engine.factory")

    seen = []

    def fake_create_engine(engine_type: str, **kwargs):
        seen.append(engine_type)
        return ("engine", engine_type)

    monkeypatch.setattr(factory_module, "create_engine", fake_create_engine)

    # Would normally pick crewai because llm_config is set
    actors = [DummyActor(llm_config={"model": "gpt"})]
    engine = EngineFactory.create(actors, engine_type="native")

    assert engine == ("engine", "native")
    assert seen == ["native"]
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


def test_factory_forced_crewai_overrides_auto(monkeypatch, caplog):
    import framework.engine.factory as factory_module

    caplog.set_level("INFO", logger="framework.engine.factory")

    seen = []

    def fake_create_engine(engine_type: str, **kwargs):
        seen.append(engine_type)
        return ("engine", engine_type)

    monkeypatch.setattr(factory_module, "create_engine", fake_create_engine)

    # Would normally pick native because llm_config is None
    actors = [DummyActor(llm_config=None)]
    engine = EngineFactory.create(actors, engine_type="crewai")

    assert engine == ("engine", "crewai")
    assert seen == ["crewai"]
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


def test_factory_unknown_engine_type_raises():
    actors = [DummyActor(llm_config=None)]
    with pytest.raises(ValueError):
        EngineFactory.create(actors, engine_type="something_else")


def test_factory_empty_actors_raises():
    with pytest.raises(ValueError):
        EngineFactory.create([])
