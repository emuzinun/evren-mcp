import zipfile
from pathlib import Path

import httpx
import pytest

from evren_mcp.errors import EvrenError
from evren_mcp.upload import precheck, upload
from tests.fakes import envelope

DS = "00000000-0000-4000-8000-000000000005"


def make_zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return path


GOOD = {"data.yaml": b"names: {0: car}\n", "images/train/a.jpg": b"A", "images/train/b.jpg": b"B",
        "labels/train/a.txt": b"0 0.5 0.5 0.1 0.1\n"}


def test_precheck_good(tmp_path):
    r = precheck(make_zip(tmp_path / "a.zip", GOOD), 100)
    assert r["gorsel"] == 2 and r["etiket"] == 1 and r["kopya"] == 0
    assert any("%80" in u for u in r["uyarilar"])


def test_precheck_unicode_path(tmp_path):
    klasor = tmp_path / "Çalışma Klasörü ğüş"
    klasor.mkdir()
    assert precheck(make_zip(klasor / "veri seti.zip", GOOD), 100)["gorsel"] == 2


@pytest.mark.parametrize("bad_name", ["../evil.jpg", "/etc/x.jpg", "C:/x.jpg", "images/../../x.jpg"])
def test_precheck_rejects_escaping_paths(tmp_path, bad_name):
    with pytest.raises(EvrenError, match="güvensiz"):
        precheck(make_zip(tmp_path / "a.zip", GOOD | {bad_name: b"x"}), 100)


def test_precheck_rejects_macos_files(tmp_path):
    with pytest.raises(EvrenError, match="macOS"):
        precheck(make_zip(tmp_path / "a.zip", GOOD | {"__MACOSX/images/._a.jpg": b"x"}), 100)


def test_precheck_requires_yaml_and_images(tmp_path):
    with pytest.raises(EvrenError, match="data.yaml"):
        precheck(make_zip(tmp_path / "a.zip", {"images/train/a.jpg": b"A"}), 100)
    with pytest.raises(EvrenError, match="görsel"):
        precheck(make_zip(tmp_path / "b.zip", {"data.yaml": b"x"}), 100)


def test_precheck_counts_duplicates_and_unlabeled(tmp_path):
    files = {"data.yaml": b"x", "images/train/a.jpg": b"A", "images/train/a2.jpg": b"A"}
    r = precheck(make_zip(tmp_path / "a.zip", files), 100)
    assert r["kopya"] == 1 and any("Etiket yok" in u for u in r["uyarilar"])


def test_precheck_size_limit_and_bad_zip(tmp_path):
    big = make_zip(tmp_path / "a.zip", GOOD)
    with pytest.raises(EvrenError, match="sınır"):
        precheck(big, 0.0000001)
    junk = tmp_path / "b.zip"
    junk.write_bytes(b"zip degil")
    with pytest.raises(EvrenError, match="zip"):
        precheck(junk, 100)


def test_upload_dry_run_sends_nothing(fake, platform, fast_settings, tmp_path):
    out = upload(platform, fast_settings, zip_path=str(make_zip(tmp_path / "a.zip", GOOD)), name="deneme")
    assert "dry_run=false" in out["not"] and fake.requests == []


def test_upload_creates_private_set_and_imports(fake, platform, fast_settings, tmp_path):
    fake.on("POST", "/datasets", (201, envelope({"id": DS})))
    fake.on("POST", f"/datasets/{DS}/import",
            lambda r: httpx.Response(200, text='{"t":"h"}\n{"t":"d","created":2,"annotations":1}\n'))
    out = upload(platform, fast_settings, zip_path=str(make_zip(tmp_path / "a.zip", GOOD)),
                 name="deneme", dry_run=False)
    assert out["set_id"] == DS and out["sonuc"]["created"] == 2
    assert b'"visibility":"private"' in fake.calls("POST", "/datasets")[0].content.replace(b" ", b"")


def test_upload_import_without_done_event_is_explained(fake, platform, fast_settings, tmp_path):
    fake.on("POST", "/datasets", (201, envelope({"id": DS})))
    fake.on("POST", f"/datasets/{DS}/import", lambda r: httpx.Response(200, text='{"t":"e","error":"bozuk"}\n'))
    with pytest.raises(EvrenError, match=DS):
        upload(platform, fast_settings, zip_path=str(make_zip(tmp_path / "a.zip", GOOD)),
               name="deneme", dry_run=False)
