import collections
import logging
import shutil
from pathlib import Path

import pytest

from llamka.llore.config import Config
from llamka.llore.pipeline import FileState, Llore
from llamka.llore.state import query_db
from llamka.llore.vector import gen_matching_snapshots, get_vector_collection
from llamka.misc import delete_file_ensure_parent_dir

state_db = delete_file_ensure_parent_dir("data/state/state.db")

srcs = ("Crypto101_fragment.pdf", "Crypto101.pdf", "DuckDB_In_Action_Final_MotherDuck.pdf")

dsts = srcs[1:]
pdf_path = Path("data/files")
tst_pdfs = Path("tests/pdfs")


@pytest.mark.debug
def test_file_state():
    ff = {f.name: FileState(f).sha256() for f in sorted(tst_pdfs.iterdir())}
    print(ff)
    assert ff == {
        "Crypto101.pdf": "527c06ac5a3e3c8f997327e76b7fa5f29caff689c55b44d7b049b77b0f209503",
        "Crypto101_fragment.pdf": "473aa1e0f98d90d2cdd326b8e33070edc875d0906a47f375c82d2859dc6be8f0",
        "DuckDB_In_Action_Final_MotherDuck.pdf": "9b20019b9d4ff021ba9e8eef79dcc935bf71ee92b3c94b21d81126723e6620c5",
    }


@pytest.mark.slow
def test_pipeline(caplog: pytest.LogCaptureFixture):
    s1_fragment, s1, s2 = (tst_pdfs / n for n in srcs)
    d1, d2 = (pdf_path / n for n in dsts)

    caplog.set_level(logging.DEBUG)
    core = Llore()
    core.process_files()
    pdf_path.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(s1_fragment, d1)
    core.process_files()
    shutil.copyfile(s1, d1)
    shutil.copyfile(s2, d2)
    core.process_files()
    (pdf_path / dsts[0]).unlink()
    core.process_files()
    (pdf_path / dsts[1]).unlink()
    core.process_files()

    with core.open_db() as conn:
        actual = query_db(
            conn,
            "select c.action_id, c.action, c.collection, a.sha256, a.error, a.n_chunks, s.source_id, s.absolute_path from RagActionCollection c, RagAction a, RagSource s Where s.source_id = a.source_id and a.action_id = c.action_id order by 1, 3",
        )
        i = len(str(Path(".").absolute())) + 1
        actual = [
            (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7][i:].replace("\\", "/"))
            for row in actual
        ]
        expected = [
            (
                1,
                "new",
                "documents",
                "473aa1e0f98d90d2cdd326b8e33070edc875d0906a47f375c82d2859dc6be8f0",
                None,
                41,
                1,
                "data/files/Crypto101.pdf",
            ),
            (
                2,
                "update",
                "documents",
                "527c06ac5a3e3c8f997327e76b7fa5f29caff689c55b44d7b049b77b0f209503",
                None,
                419,
                1,
                "data/files/Crypto101.pdf",
            ),
            (
                3,
                "new",
                "documents",
                "9b20019b9d4ff021ba9e8eef79dcc935bf71ee92b3c94b21d81126723e6620c5",
                None,
                863,
                2,
                "data/files/DuckDB_In_Action_Final_MotherDuck.pdf",
            ),
            (
                4,
                "delete",
                "documents",
                "",
                None,
                0,
                1,
                "data/files/Crypto101.pdf",
            ),
            (
                5,
                "delete",
                "documents",
                "",
                None,
                0,
                2,
                "data/files/DuckDB_In_Action_Final_MotherDuck.pdf",
            ),
        ]
        for a, e in zip(actual, expected, strict=False):
            assert a == e


@pytest.mark.debug
def test_vector_db(caplog: pytest.LogCaptureFixture):
    core = Llore()
    caplog.set_level(logging.DEBUG)
    get_vector_collection(core.config, "documents")
    categories = collections.Counter(e.name for e in caplog.records)
    assert "urllib3.connectionpool" not in categories


@pytest.mark.debug
def test_snapshot_cache():
    cfg: Config = Llore().config

    assert list(gen_matching_snapshots(cfg.hf_hub_dir, "all-MiniLM-L6-v2")) == [
        "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf",
    ]
