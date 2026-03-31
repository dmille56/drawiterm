from drawiterm.commands import MoveElementsCommand
from drawiterm.models import (
    ArrowElement,
    DiamondElement,
    Document,
    EllipseElement,
    RectElement,
    TextElement,
    _orthogonal_arrow_cells,
    find_anchor_near,
)


def test_text_bounding_box_simple():
    t = TextElement(id=1, col=2, row=3, text="hi")
    assert t.bounding_box() == (2, 3, 2, 1)


def test_text_bounding_box_multiline():
    t = TextElement(id=1, col=0, row=0, text="a\nbc\n")
    # trailing newline produces an empty last line -> width should be max(len) == 2, height == 3
    assert t.bounding_box() == (0, 0, 2, 3)


def test_orthogonal_arrow_cells_horizontal():
    cells = _orthogonal_arrow_cells(0, 0, 3, 0)
    assert cells == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_orthogonal_arrow_cells_corner_h_then_v():
    cells = _orthogonal_arrow_cells(0, 0, 2, 2)
    # If wider or equal, expect H→V routing (0,0)->(2,0)->(2,2)
    assert cells[0] == (0, 0)
    assert (2, 0) in cells
    assert (2, 2) in cells


def test_rect_anchor_points_ordering():
    rect = RectElement(id=1, col=0, row=0, width=5, height=4)
    anchors = rect.anchor_points()
    assert [a.name for a in anchors] == [
        "top",
        "top-right",
        "right",
        "bottom-right",
        "bottom",
        "bottom-left",
        "left",
        "top-left",
    ]


def test_ellipse_anchor_points_positions():
    ellipse = EllipseElement(id=2, col=10, row=5, width=4, height=4)
    anchors = {a.name: (a.col, a.row) for a in ellipse.anchor_points()}
    assert anchors["top"] == (11, 5)
    assert anchors["right"] == (13, 6)
    assert anchors["bottom"] == (11, 8)
    assert anchors["left"] == (10, 6)


def test_diamond_anchor_points_positions():
    diamond = DiamondElement(id=3, col=2, row=2, width=6, height=5)
    anchors = {a.name: (a.col, a.row) for a in diamond.anchor_points()}
    assert anchors["top"] == (5, 2)
    assert anchors["right"] == (7, 4)
    assert anchors["bottom"] == (5, 6)
    assert anchors["left"] == (2, 4)


def test_find_anchor_near_snaps_to_top_mid():
    rect = RectElement(id=1, col=0, row=0, width=6, height=4)
    doc = Document(elements=[rect])
    anchor = find_anchor_near(doc, 2, 0)
    assert anchor is not None
    assert anchor.name == "top"


def test_arrow_serialization_includes_anchor_names():
    arrow = ArrowElement(
        id=3,
        start_col=0,
        start_row=0,
        end_col=1,
        end_row=1,
        start_element_id=1,
        end_element_id=2,
        start_anchor="left",
        end_anchor="bottom",
    )
    data = arrow.to_dict()
    rehydrated = ArrowElement.from_dict(data)
    assert rehydrated.start_anchor == "left"
    assert rehydrated.end_anchor == "bottom"
    assert rehydrated.start_element_id == 1
    assert rehydrated.end_element_id == 2


def test_move_shape_updates_attached_arrow():
    rect = RectElement(id=1, col=0, row=0, width=4, height=3)
    arrow = ArrowElement(
        id=2,
        start_col=0,
        start_row=0,
        end_col=10,
        end_row=0,
        start_element_id=rect.id,
        start_anchor="right",
    )
    doc = Document(elements=[rect, arrow])
    original_anchor = next(a.col for a in rect.anchor_points() if a.name == "right")
    assert arrow.start_col == original_anchor
    cmd = MoveElementsCommand([(rect.id, 2, 1)])
    cmd.execute(doc)
    moved_anchor = next((a.col, a.row) for a in rect.anchor_points() if a.name == "right")
    assert (arrow.start_col, arrow.start_row) == moved_anchor
    cmd.undo(doc)
    original_anchor_point = next((a.col, a.row) for a in rect.anchor_points() if a.name == "right")
    assert (arrow.start_col, arrow.start_row) == original_anchor_point
