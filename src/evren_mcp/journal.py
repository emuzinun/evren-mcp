"""Yerel eğitim günlüğü (JSONL). 20–21.09'da 34 eğitim hiçbir yere yazılmadığı
için API'den geri kurulmak zorunda kalındı (yazarın ölçümlerinde); her başlatma ve bitiş
buraya düşer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: str, **data) -> dict | None:
        """Kaydı yazar; yazılamazsa (disk, izin) `None` döner, istisna fırlatmaz —
        platformda başlamış bir işin kimliği günlük hatası yüzünden kaybolmasın."""
        rec = {"zaman": datetime.now(UTC).isoformat(timespec="seconds"), "olay": event, **data}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            return None
        return rec

    def read(self, limit: int = 50) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out[-limit:]

    def find(self, event: str, job_id: str) -> dict | None:
        for rec in reversed(self.read(limit=10_000)):
            if rec.get("olay") == event and rec.get("is_id") == job_id:
                return rec
        return None
