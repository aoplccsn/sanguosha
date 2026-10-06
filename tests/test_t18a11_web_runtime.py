from sanguosha.web import __main__ as startup


def test_windows_uvicorn_uses_explicit_socket_factory(monkeypatch):
    monkeypatch.setattr(startup.sys,'platform','win32')
    monkeypatch.setattr(startup.asyncio,'set_event_loop_policy',lambda _: (_ for _ in ()).throw(AssertionError('global policy cannot override modern uvicorn')))
    assert startup.web_loop()=='sanguosha.web.__main__:socket_loop_factory'
    sentinel=object()
    monkeypatch.setattr(startup.asyncio,'SelectorEventLoop',lambda:sentinel)
    assert startup.socket_loop_factory() is sentinel


def test_other_platforms_keep_default_event_loop(monkeypatch):
    monkeypatch.setattr(startup.sys,'platform','linux')
    assert startup.web_loop()=='auto'


def test_older_uvicorn_uses_windows_selector_policy(monkeypatch):
    sentinel=object();calls=[]
    monkeypatch.setattr(startup.sys,'platform','win32')
    monkeypatch.setattr(startup.uvicorn,'Config',object)
    monkeypatch.setattr(startup.asyncio,'WindowsSelectorEventLoopPolicy',lambda:sentinel,raising=False)
    monkeypatch.setattr(startup.asyncio,'set_event_loop_policy',calls.append)
    assert startup.web_loop()=='asyncio'
    assert calls==[sentinel]
