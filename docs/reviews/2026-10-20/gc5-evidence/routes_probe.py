"""G-C5 item 6 through HTTP via tests/support/routes.py::route_client. Run from src/backend with measure.py's dir on sys.path:
python <this dir>/routes_probe.py   (sockets blocked, HF offline, via measure.py import)."""
import asyncio, logging, os, sys, uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.getcwd())
sys.path.insert(0, str(Path(__file__).parent))
import measure  # noqa: E402  (blocks sockets, sets offline env)
from measure import enable_flag  # noqa: E402

import api.assistant as A  # noqa: E402
import api.interpretations as I  # noqa: E402
import models  # noqa: E402,F401
from core.auth import get_profile_db_session  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import Base  # noqa: E402
from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models import Observation  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from tests.legacy_eval import harness  # noqa: E402
from tests.support.routes import route_client  # noqa: E402

ANSWER = "REPORT FACTS:\nYour glucose was 95 mg/dL [cite:1].\n\nGENERAL INFO:\nNormal fasting glucose is typically 70-100 mg/dL [cite:2]."


class Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.recs = []

    def emit(self, r):
        self.recs.append(r)


def _warns(cap):
    return [x.getMessage() for x in cap.recs if x.levelno >= logging.WARNING and "NLI" in x.getMessage()]


def chat():
    cap = Cap(); logging.getLogger().addHandler(cap)
    # harness.legacy_chat_client wraps tests.support.routes.route_client(assistant_api.router, "/assistant")
    with harness.legacy_chat_client(harness.build_chunks("glucose"), ANSWER) as (client, _append):
        try:
            r = client.post("/assistant/chat", json={"question": "Is my glucose in the usual range?"})
            out = (r.status_code, "uncertainty" if '"segment_type":"uncertainty"' in r.text else "answer-segments", r.text[:90])
        except Exception as e:
            out = ("EXC", type(e).__name__, str(e)[:90])
    logging.getLogger().removeHandler(cap)
    return out, len(_warns(cap))


async def _dbs():
    sessions = []
    for base in (ProfileDatabaseBase, Base):
        eng = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with eng.begin() as c:
            await c.run_sync(base.metadata.create_all)
        sessions.append(AsyncSession(eng, expire_on_commit=False))
    pdb, mdb = sessions
    obs = Observation(id=str(uuid.uuid4()), profile_id="profile-a", doc_id=str(uuid.uuid4()), analyte_canonical="glucose",
                      analyte_raw="Glucose", value=95.0, unit="mg/dL", ref_low=70.0, ref_high=100.0, collected_at=datetime(2026, 3, 1, 9))
    pdb.add(obs); await pdb.commit()
    return pdb, mdb, obs.id


def grounded():
    loop = asyncio.new_event_loop()
    pdb, mdb, oid = loop.run_until_complete(_dbs())
    cap = Cap(); logging.getLogger().addHandler(cap)
    rag = A.get_rag_module()
    rag.retrieve_context = AsyncMock(return_value=harness.build_chunks("glucose"))
    rag._generate_with_runner = AsyncMock(return_value=ANSWER)
    with patch.object(I, "get_rag_module", return_value=rag):
        with route_client(I.router, "/interpretations", profile_id="profile-a", master_db=mdb, raise_server_exceptions=False) as client:
            async def ov():
                return pdb
            client.app.dependency_overrides[get_profile_db_session] = ov
            r = client.post(f"/interpretations/observations/{oid}/interpret-grounded")
    logging.getLogger().removeHandler(cap)
    try:
        j = r.json(); v = j.get("verification") or {}
        out = (r.status_code, dict(is_valid=j.get("is_valid"), verified=v.get("verified_claims"), failed=v.get("failed_claims"),
                                   faithfulness=v.get("faithfulness_score"), segments=len(j.get("grounded_segments", [])), detail=j.get("detail")))
    except Exception:
        out = (r.status_code, r.text[:60])
    return out, len(_warns(cap))


def scenario(name, setup):
    enable_flag(True); undo = setup()
    try:
        print(f"--- {name} ---")
        print(" POST /assistant/chat                              ->", *chat())
        print(" POST /interpretations/observations/{id}/interpret-grounded ->", *grounded())
    finally:
        undo()


def absent():
    old = settings.nli_model_path; settings.nli_model_path = "/nonexistent/nli"
    import modules.embeddings as E; E._nli_encoder = None
    return lambda: setattr(settings, "nli_model_path", old)


def patch_predict(fn):
    from sentence_transformers import CrossEncoder
    orig = CrossEncoder.predict; CrossEncoder.predict = fn
    return lambda: setattr(CrossEncoder, "predict", orig)


def boom(self, *a, **k):
    raise RuntimeError("forced predict failure")


def weird(self, *a, **k):
    import numpy as np
    return np.array([[0.1, 0.1, 0.1, 0.7]])  # index 3 has no label


if __name__ == "__main__":
    print("--- flag off (baseline) ---"); enable_flag(False)
    print(" POST /assistant/chat ->", *chat()); print(" interpret-grounded   ->", *grounded())
    scenario("flag on, model present (real predict)", lambda: (lambda: None))
    scenario("flag on, model absent", absent)
    scenario("flag on, predict raises RuntimeError", lambda: patch_predict(boom))
    scenario("flag on, predict returns unmapped label index", lambda: patch_predict(weird))
    print("socket attempts", len(measure.SOCK_ATTEMPTS))
