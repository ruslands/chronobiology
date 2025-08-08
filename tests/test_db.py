import types
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from chronobiology import db


class DummyClient:
    def __init__(self, *args, **kwargs):
        pass

    def query(self, query):
        return types.SimpleNamespace(raw={"series": [{"values": [("m1",), ("m2",)]}]})

    def close(self):
        pass


def test_get_measurements(monkeypatch):
    monkeypatch.setattr(db, "InfluxDBClient", DummyClient)
    q = db.DBQuery("db", "user", "pass")
    assert q.get_measurements() == ["m1", "m2"]
