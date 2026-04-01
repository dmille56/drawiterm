import json

from drawiterm.file_io import load, save
from drawiterm.models import ArrowElement, Document, SCHEMA_VERSION, TextElement


def test_roundtrip_save_load(tmp_path):
    doc = Document()
    t = TextElement(id=doc.next_id(), z_order=1, col=0, row=0, text="hello")
    a = ArrowElement(
        id=doc.next_id(),
        z_order=2,
        start_col=0,
        start_row=0,
        end_col=3,
        end_row=0,
        label="L",
    )
    doc.add(t)
    doc.add(a)
    path = tmp_path / "a.drawiterm"
    save(doc, path)
    doc2 = load(path)
    assert any(isinstance(e, TextElement) and e.text == "hello" for e in doc2.elements)
    assert any(isinstance(e, ArrowElement) and e.label == "L" for e in doc2.elements)
    assert doc2.schema_version == SCHEMA_VERSION


def test_migration_adds_missing_anchor_fields(tmp_path):
    raw = {
        "schema_version": SCHEMA_VERSION - 1,
        "title": "Old",
        "elements": [
            {
                "id": 1,
                "element_type": "arrow",
                "z_order": 1,
                "start_col": 0,
                "start_row": 0,
                "end_col": 1,
                "end_row": 1,
            }
        ],
    }
    path = tmp_path / "old.drawiterm"
    path.write_text(json.dumps(raw), encoding="utf-8")
    doc = load(path)
    assert doc.schema_version == SCHEMA_VERSION
    arrow = next(e for e in doc.elements if isinstance(e, ArrowElement))
    assert arrow.start_anchor is None and arrow.end_anchor is None
