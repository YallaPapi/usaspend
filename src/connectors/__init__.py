from . import sec, usaspending, sbir

CONNECTORS = {
    "sec": sec.fetch,
    "usaspending": usaspending.fetch,
    "sbir": sbir.fetch,
}

__all__ = ["CONNECTORS"]

