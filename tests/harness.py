"""Deterministic harness: a fake `genlayer` module so the contract runs under plain unittest/pytest."""
import importlib.util
import pathlib
import sys
import types


class UserError(Exception):
    pass


class Address:
    def __init__(self, hx):
        self.as_hex = hx

    def __eq__(self, o):
        return isinstance(o, Address) and o.as_hex == self.as_hex

    def __hash__(self):
        return hash(self.as_hex)


class TreeMap(dict):
    def __class_getitem__(cls, item):
        return cls


class World:
    def __init__(self):
        self.pages, self.llm, self.llm_calls, self.principles = {}, None, [], []


WORLD = World()
STATE = types.SimpleNamespace(sender=None)


def reset_world():
    WORLD.__init__()


def _render(url, mode="text"):
    v = WORLD.pages.get(url)
    if v is None or isinstance(v, Exception):
        raise RuntimeError("fetch failed")
    return v


def _exec_prompt(prompt, response_format="text"):
    WORLD.llm_calls.append(prompt)
    out = WORLD.llm(prompt) if callable(WORLD.llm) else WORLD.llm
    if isinstance(out, Exception):
        raise out
    return out


def _prompt_comparative(fn, principle):
    WORLD.principles.append(principle)
    return fn()


class _Msg:
    @property
    def sender_address(self):
        return STATE.sender


gl = types.SimpleNamespace(
    Contract=object,
    public=types.SimpleNamespace(view=lambda f: f, write=lambda f: f),
    message=_Msg(),
    vm=types.SimpleNamespace(UserError=UserError),
    nondet=types.SimpleNamespace(
        web=types.SimpleNamespace(render=_render), exec_prompt=_exec_prompt
    ),
    eq_principle=types.SimpleNamespace(prompt_comparative=_prompt_comparative),
)

_mod = types.ModuleType("genlayer")
_mod.gl, _mod.Address, _mod.TreeMap, _mod.u256 = gl, Address, TreeMap, int
_mod.__all__ = ["gl", "Address", "TreeMap", "u256"]
sys.modules["genlayer"] = _mod

_PATH = pathlib.Path(__file__).parent.parent / "contracts" / "decentralized_ai_auditor.py"
_spec = importlib.util.spec_from_file_location("auditor_contract", _PATH)
auditor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditor)

OWNER = Address("0x" + "01" * 20)
ALICE = Address("0x" + "aa" * 20)
BOB = Address("0x" + "bb" * 20)
CAROL = Address("0x" + "cc" * 20)
DAVE = Address("0x" + "dd" * 20)
EVE = Address("0x" + "ee" * 20)
STATE.sender = ALICE


def deploy(sender=OWNER):
    STATE.sender = sender
    cls = auditor.DecentralizedAIAuditor
    c = cls.__new__(cls)
    for name, ann in cls.__annotations__.items():
        if ann is TreeMap:
            setattr(c, name, TreeMap())
        elif ann is bool:
            setattr(c, name, False)
        elif ann is str:
            setattr(c, name, "")
        elif ann is int:
            setattr(c, name, 0)
        elif ann is Address:
            setattr(c, name, Address("0x" + "00" * 20))
    c.__init__()
    STATE.sender = ALICE
    return c


def as_user(addr):
    STATE.sender = addr


URL1 = "https://example.org/eiffel"
URL2 = "https://www.britannica.com/eiffel"
URL3 = "https://notes.example.net/late"
PAGE = ("The Eiffel Tower was completed in 1889 and stands 330 metres tall in Paris. "
        "It was designed by the engineering company of Gustave Eiffel.")
PAGE3 = "A note: the Eiffel Tower was completed in 1887 according to this note, claims the author."
CLAIM = "The Eiffel Tower was completed in 1889."
Q1 = "The Eiffel Tower was completed in 1889"
Q2 = "stands 330 metres tall in Paris"
Q3 = "completed in 1887 according to this note"


def ev(idx, quote, stance):
    return {"source_index": idx, "quote": quote, "stance": stance}


def verdict_json(verdict="SUPPORTED", conf=90, evidence=None, rationale="ok"):
    if evidence is None:
        evidence = [ev(0, Q1, "supports"), ev(0, Q2, "supports")]
    return {"verdict": verdict, "confidence": conf, "rationale": rationale, "evidence": evidence}


def setup_world(llm=None, pages=None):
    reset_world()
    WORLD.pages = pages if pages is not None else {URL1: PAGE, URL2: PAGE, URL3: PAGE3}
    WORLD.llm = llm if llm is not None else verdict_json()
