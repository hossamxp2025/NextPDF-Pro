"""Digital signing, checked against a real signature rather than a mock.

Every test here signs an actual PDF with the self-signed certificate in
tests/certificates/ and reads the result back through pyHanko's validator. The
certificate is a test fixture with no authority, which is exactly why these
tests can prove the point the module exists to make: a file can be provably
unchanged and still not be trusted, and the two must be reported apart.
"""
import os
import shutil

import pymupdf as fitz
import pytest

from src.engine.signing import (
    Placement,
    SigningError,
    describe_certificate,
    has_signatures,
    sign_document,
    verify_document,
)

CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certificates")
P12 = os.path.join(CERT_DIR, "test-signer.p12")
ROOT = os.path.join(CERT_DIR, "test-signer.crt")
PASSWORD = "nextpdf-test"

pytestmark = pytest.mark.skipif(
    not os.path.isfile(P12),
    reason="run scripts/make_test_certificate.py to create the test certificate",
)


@pytest.fixture
def document(tmp_path):
    path = tmp_path / "source.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Signed document test", fontsize=14)
    # Uncompressed so the tampering test can find a byte to change and point
    # at it, rather than flipping a byte at a guessed offset.
    doc.save(str(path), deflate=False)
    doc.close()
    return str(path)


def test_the_test_certificate_reads_back_as_self_signed():
    details = describe_certificate(P12, PASSWORD)
    assert details["self_signed"] is True
    assert details["expired"] is False
    assert "Test" in details["subject"]


def test_a_wrong_password_is_refused_with_a_reason():
    with pytest.raises(SigningError) as error:
        describe_certificate(P12, "not-the-password")
    assert "password" in str(error.value).lower()


def test_signing_writes_a_new_file_and_leaves_the_source_alone(document, tmp_path):
    before = open(document, "rb").read()
    output = str(tmp_path / "signed.pdf")

    result = sign_document(document, output, P12, PASSWORD, reason="Approved")

    assert os.path.isfile(output)
    assert open(document, "rb").read() == before, "the source file was modified"
    assert result["visible"] is False
    assert result["timestamped_by_authority"] is False


def test_signing_in_place_is_refused(document):
    with pytest.raises(SigningError):
        sign_document(document, document, P12, PASSWORD)


def test_a_fresh_signature_is_intact_and_covers_the_whole_file(document, tmp_path):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD, reason="Approved")

    reports = verify_document(output, trust_roots=[ROOT])
    assert len(reports) == 1
    report = reports[0]
    assert report.intact is True
    assert report.valid is True
    assert report.unchanged_since_signing is True
    assert report.covers_whole_file is True


def test_without_trust_roots_nothing_is_called_trusted(document, tmp_path):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD)

    report = verify_document(output)[0]
    assert report.intact is True, "the bytes are still provably unchanged"
    assert report.trusted is False
    assert report.trust_problem, "an untrusted result must say why"


def test_the_self_signed_certificate_is_trusted_only_when_supplied(document, tmp_path):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD)

    assert verify_document(output, trust_roots=[ROOT])[0].trusted is True
    assert verify_document(output, trust_roots=[])[0].trusted is False


def test_every_report_says_there_is_no_trusted_timestamp(document, tmp_path):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD)

    notes = " ".join(verify_document(output, trust_roots=[ROOT])[0].notes).lower()
    assert "timestamp" in notes


def test_changing_a_byte_of_the_signed_file_is_detected(document, tmp_path):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD)
    tampered = str(tmp_path / "tampered.pdf")
    shutil.copyfile(output, tampered)

    # MuPDF writes the page text as a hex string, so that is what to look for.
    original = b"Signed".hex().encode("ascii")
    data = bytearray(open(tampered, "rb").read())
    marker = data.find(original)
    assert marker != -1, "the test needs the page text to still be findable"
    data[marker:marker + len(original)] = b"Forged".hex().encode("ascii")
    open(tampered, "wb").write(bytes(data))

    report = verify_document(tampered, trust_roots=[ROOT])[0]
    assert report.unchanged_since_signing is False


def test_appending_to_a_signed_file_shows_as_not_covering_the_whole_file(
    document, tmp_path
):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD)
    grown = str(tmp_path / "grown.pdf")
    shutil.copyfile(output, grown)
    with open(grown, "ab") as handle:
        handle.write(b"\n% a later addition\n")

    report = verify_document(grown, trust_roots=[ROOT])[0]
    assert report.covers_whole_file is False
    assert any("added" in note.lower() for note in report.notes)


def test_a_visible_signature_is_drawn_on_the_page_asked_for(document, tmp_path):
    output = str(tmp_path / "visible.pdf")
    placement = Placement(page=0, rect=(72.0, 600.0, 300.0, 680.0))

    result = sign_document(document, output, P12, PASSWORD,
                           placement=placement, signer_label="حسام الفاخرة")

    assert result["visible"] is True
    with fitz.open(output) as signed:
        widgets = list(signed.load_page(0).widgets())
    assert widgets, "a visible signature must leave a widget on the page"
    assert verify_document(output, trust_roots=[ROOT])[0].intact is True


def test_a_visible_signature_area_that_is_too_small_is_refused(document, tmp_path):
    with pytest.raises(SigningError):
        sign_document(document, str(tmp_path / "x.pdf"), P12, PASSWORD,
                      placement=Placement(page=0, rect=(10, 10, 15, 15)))


def test_a_page_that_does_not_exist_is_refused(document, tmp_path):
    with pytest.raises(SigningError):
        sign_document(document, str(tmp_path / "x.pdf"), P12, PASSWORD,
                      placement=Placement(page=9, rect=(72, 600, 300, 680)))


def test_an_unsigned_document_reports_no_signatures(document):
    assert verify_document(document) == []
    assert has_signatures(document) is False


def test_a_signed_document_reports_that_it_has_one(document, tmp_path):
    output = str(tmp_path / "signed.pdf")
    sign_document(document, output, P12, PASSWORD)
    assert has_signatures(output) is True


def test_a_missing_certificate_is_refused(document, tmp_path):
    with pytest.raises(SigningError):
        sign_document(document, str(tmp_path / "x.pdf"),
                      str(tmp_path / "nope.p12"), PASSWORD)
