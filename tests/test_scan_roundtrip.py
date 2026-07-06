"""Digital round trip: build the fixture paper → rasterize → scan → crop.

This is the offline stand-in for the physical Phase 1 exit criterion (print,
sit, scan). It exercises the whole chain: layout → typst → PDF → raster →
registration deskew → QR match → manifest cropping — including a 180°-rotated,
skewed, noisy "photocopy" to prove orientation recovery.
"""

import importlib.util
import json

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pdfium = pytest.importorskip("pypdfium2")
if importlib.util.find_spec("typst") is None:
    pytest.skip("typst not installed", allow_module_level=True)

from markable.build import build_package
from markable.ingest import ingest_markdown
from markable.models import PageStatus, ScanReport
from markable.scan import scan_package


@pytest.fixture(scope="module")
def package(tmp_path_factory, request):
    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    assessment = ingest_markdown(draft, assume_yes=True)
    pkg = tmp_path_factory.mktemp("pkg") / "demo"
    build_package(assessment, pkg, compile_pdf=True)
    return pkg


@pytest.fixture(scope="module")
def scans(package, tmp_path_factory):
    """Rasterize the built paper into synthetic scans: one clean set, one
    rotated+skewed+noisy set."""
    out = tmp_path_factory.mktemp("scans")
    doc = pdfium.PdfDocument(str(package / "paper.pdf"))
    pages = []
    for i in range(len(doc)):
        arr = doc[i].render(scale=300 / 72).to_numpy()
        if arr.ndim == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2GRAY if arr.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
        pages.append(arr)
    doc.close()

    rng = np.random.default_rng(7)
    files = []
    for i, arr in enumerate(pages, 1):
        clean = out / f"sA_p{i}.png"
        cv2.imwrite(str(clean), arr)
        files.append(clean)

        messy = cv2.rotate(arr, cv2.ROTATE_180)
        h, w = messy.shape
        m = cv2.getRotationMatrix2D((w / 2, h / 2), 1.5, 0.985)
        messy = cv2.warpAffine(messy, m, (w, h), borderValue=255)
        messy = np.clip(messy.astype(np.float64) + rng.normal(0, 6, messy.shape), 0, 255).astype(np.uint8)
        path = out / f"sB_p{i}.png"
        cv2.imwrite(str(path), messy)
        files.append(path)
    return files


@pytest.fixture(scope="module")
def report(package, scans) -> ScanReport:
    id_map = {f.name: ("S1001" if f.name.startswith("sA") else "S1002") for f in scans}
    return scan_package(package, scans, id_map=id_map)


def test_every_page_matches(report):
    assert all(p.status is PageStatus.ok for p in report.pages), [
        (p.source, p.status, p.detail) for p in report.pages
    ]


def test_full_coverage_for_both_students(report):
    by_id = {s.student_id: s for s in report.students}
    assert set(by_id) == {"S1001", "S1002"}
    for s in by_id.values():
        assert s.pages_missing == []


def test_crops_exist_for_every_zone(package, report):
    manifest = json.loads((package / "manifest.json").read_text())
    all_qids = {z["question_id"] for page in manifest["pages"] for z in page["zones"]}
    for sid in ("S1001", "S1002"):
        crops = {p.stem for p in (package / "scripts" / sid).glob("*.png") if not p.stem.endswith("_final")}
        assert crops == all_qids


def test_numerical_final_answer_crop_written(package):
    assert (package / "scripts" / "S1002" / "Q3_final.png").exists()


def test_rotated_scan_crop_is_upright(package):
    """The Q1 crop from the 180°-rotated scan must contain dark bubble outlines
    in the expected place — i.e. the page was recovered upright, not upside down."""
    a = cv2.imread(str(package / "scripts" / "S1001" / "Q1.png"), cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(str(package / "scripts" / "S1002" / "Q1.png"), cv2.IMREAD_GRAYSCALE)
    assert a.shape[0] > 0 and b.shape
    # Same zone from the same paper: sizes agree within a couple of mm...
    assert abs(a.shape[0] - b.shape[0]) < 30 and abs(a.shape[1] - b.shape[1]) < 30
    # ...and the rotated crop's ink lands where the clean crop's ink does.
    bb = cv2.resize(b, (a.shape[1], a.shape[0]))
    ink_a, ink_b = a < 128, bb < 128
    overlap = (ink_a & ink_b).sum() / max(1, ink_a.sum())
    assert overlap > 0.5, f"only {overlap:.0%} of ink overlaps — crop misaligned or flipped"


def test_wrong_test_scan_rejected(package, tmp_path):
    """A page whose QR belongs to a different paper version must be refused."""
    from markable import qr as qr_mod
    from markable.build import layout

    # Fabricate an A4 page with valid fiducials but a foreign QR payload.
    dpi = 300
    ppm = dpi / 25.4
    w, h = round(210 * ppm), round(297 * ppm)
    img = np.full((h, w), 255, np.uint8)
    reg = layout.registration_marks()
    half = round(layout.REG_SIZE * ppm / 2)
    for cx, cy in [reg.top_left, reg.top_right, reg.bottom_left, reg.bottom_right]:
        x, y = round(cx * ppm), round(cy * ppm)
        img[y - half:y + half, x - half:x + half] = 0
    qr_png = tmp_path / "qr.png"
    qr_mod.write_png(qr_mod.make_payload("OTHER-TEST", "deadbeef0000", 1), qr_png, scale=6)
    qr_img = cv2.imread(str(qr_png), cv2.IMREAD_GRAYSCALE)
    x0, y0 = round(layout.QR_X * ppm), round(layout.QR_Y * ppm)
    img[y0:y0 + qr_img.shape[0], x0:x0 + qr_img.shape[1]] = qr_img
    scan_file = tmp_path / "foreign.png"
    cv2.imwrite(str(scan_file), img)

    rep = scan_package(package, [scan_file], id_map={"foreign.png": "SX"})
    assert rep.pages[-1].status is PageStatus.wrong_test
