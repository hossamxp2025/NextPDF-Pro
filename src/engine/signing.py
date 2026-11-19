"""Digital signatures: PKCS#12 signing, and verification that tells the truth.

A digital signature is not the visible stamp in :mod:`src.engine.stamps`. The
stamp is a picture; this is a cryptographic seal over the bytes of the file. It
says two separate things, and they must never be reported as one:

* **intact** - the bytes covered by the signature have not changed since it was
  made. This is decided by arithmetic alone and is always knowable.
* **trusted** - the certificate chains up to an authority the verifier was told
  to trust. This depends entirely on which roots were supplied. A self-signed
  certificate is never trusted, no matter how intact the file is.

:func:`verify_document` therefore reports the two separately, and a caller that
collapses them into one "valid" tick is lying to the user.

What this module does not do: it does not add a trusted timestamp from a time
server, and it does not embed revocation data (PAdES B-LT/LTA). Without those a
signature cannot be proved to have existed before the certificate expired. The
reports say so rather than leaving it to be assumed.
"""
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger("NextPDF")

#: The field name used when the caller does not choose one.
DEFAULT_FIELD_NAME = "NextPDFSignature"

#: The smallest visible signature worth drawing, in points.
MIN_VISIBLE_SIDE = 20.0

_ARABIC_FONT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "fonts", "NotoNaskhArabic-Regular.ttf",
)


class SigningError(Exception):
    """Raised with a sentence meant for the user, never a library traceback."""


@dataclass(frozen=True)
class Placement:
    """Where a visible signature goes, in the viewer's own coordinates.

    *rect* is (x0, top, x1, bottom) with the origin at the top-left of the page,
    which is what MuPDF and the viewer use. PDF itself measures from the
    bottom-left, and the conversion happens here so no caller has to think
    about it.
    """
    page: int
    rect: Tuple[float, float, float, float]


@dataclass
class SignatureReport:
    """One signature found in a file, described without overstatement."""
    field_name: str
    signer: str
    intact: bool
    valid: bool
    trusted: bool
    covers_whole_file: bool
    signed_at: Optional[datetime] = None
    reason: str = ""
    location: str = ""
    trust_problem: str = ""
    notes: List[str] = field(default_factory=list)

    @property
    def unchanged_since_signing(self) -> bool:
        """The honest headline: the content under this signature is untouched."""
        return bool(self.intact and self.valid)


_PKCS12_REFUSED = (
    "No signing key could be read from the certificate. The password is "
    "probably wrong, or the file is not a PKCS#12 certificate with a private "
    "key in it."
)


def _require_pyhanko():
    try:
        from pyhanko.sign import signers  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise SigningError(
            "The signing library (pyHanko) is not installed in this build"
        ) from exc


def describe_certificate(certificate_path: str, password: str) -> dict:
    """Read a PKCS#12 file and say whose it is, without signing anything.

    The dialog calls this before signing so the user sees which identity is
    about to be used, and so a wrong password is reported there rather than
    halfway through writing a file.
    """
    _require_pyhanko()
    from pyhanko.sign import signers

    if not os.path.isfile(certificate_path):
        raise SigningError("The certificate file was not found")
    try:
        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=certificate_path,
            passphrase=(password or "").encode("utf-8"),
        )
    except Exception as exc:
        logger.info("PKCS#12 could not be opened: %s", exc)
        raise SigningError(
            "The certificate could not be opened. The password may be wrong, "
            "or the file may not be a PKCS#12 certificate."
        ) from exc
    if signer is None:
        # pyHanko logs the underlying error and returns None rather than
        # raising, so a wrong password arrives here looking like a bad file.
        # The two cannot be told apart from the outside; say both.
        raise SigningError(_PKCS12_REFUSED)

    certificate = signer.signing_cert
    not_after = getattr(certificate, "not_valid_after", None)
    expired = bool(not_after and not_after < datetime.now(not_after.tzinfo))
    return {
        "subject": _common_name(certificate),
        "issuer": _common_name(certificate, issuer=True),
        "self_signed": _common_name(certificate) == _common_name(certificate, True),
        "valid_from": getattr(certificate, "not_valid_before", None),
        "valid_until": not_after,
        "expired": expired,
        "serial": getattr(certificate, "serial_number", None),
    }


def _common_name(certificate, issuer: bool = False) -> str:
    """The certificate's common name, or its whole subject when it has none."""
    try:
        name = certificate.issuer if issuer else certificate.subject
        native = name.native or {}
        return (native.get("common_name")
                or native.get("organization_name")
                or str(name.human_friendly))
    except Exception:
        return ""


def _pdf_box(placement: Placement, page_height: float) -> Tuple[float, float, float, float]:
    """Turn a top-left rectangle into the bottom-left box PDF wants."""
    x0, top, x1, bottom = (float(value) for value in placement.rect)
    left, right = min(x0, x1), max(x0, x1)
    upper, lower = min(top, bottom), max(top, bottom)
    if (right - left) < MIN_VISIBLE_SIDE or (lower - upper) < MIN_VISIBLE_SIDE:
        raise SigningError("The signature area is too small to draw into")
    return (left, page_height - lower, right, page_height - upper)


def _page_height(path: str, page_index: int) -> float:
    import pymupdf as fitz

    with fitz.open(path) as document:
        if page_index < 0 or page_index >= document.page_count:
            raise SigningError("That page does not exist in this document")
        return float(document.load_page(page_index).rect.height)


def _stamp_style(signer_label: str):
    """A visible appearance that can draw Arabic.

    pyHanko's default appearance uses a standard PDF font, which has no Arabic
    glyphs at all; a signature stamped with an Arabic name would come out empty
    or as boxes. The project already ships a Naskh font for exactly this, so it
    is embedded here too.
    """
    from pyhanko import stamp
    from pyhanko.pdf_utils import text as pdf_text

    text_style = None
    if os.path.isfile(_ARABIC_FONT):
        try:
            from pyhanko.pdf_utils.font import opentype

            text_style = pdf_text.TextBoxStyle(
                font=opentype.GlyphAccumulatorFactory(_ARABIC_FONT),
                font_size=9,
            )
        except Exception as exc:  # pragma: no cover - optional extra
            logger.info("Arabic font for the signature stamp unavailable: %s", exc)
            text_style = None

    body = "%(signer)s\n%(ts)s"
    if signer_label:
        body = signer_label + "\n%(ts)s"
    if text_style is None:
        return stamp.TextStampStyle(stamp_text=body)
    return stamp.TextStampStyle(stamp_text=body, text_box_style=text_style)


def sign_document(source_path: str,
                  output_path: str,
                  certificate_path: str,
                  password: str,
                  *,
                  reason: str = "",
                  location: str = "",
                  contact: str = "",
                  field_name: str = DEFAULT_FIELD_NAME,
                  placement: Optional[Placement] = None,
                  signer_label: str = "") -> dict:
    """Sign *source_path* and write the signed file to *output_path*.

    The source file is never modified. A signature is added as an incremental
    update, so every earlier revision of the document stays inside the new file
    exactly as it was - that is what lets a reader prove nothing changed.

    With *placement* the signature is also drawn on the page; without it the
    signature is there but invisible, which is normal and no weaker.
    """
    _require_pyhanko()
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import fields, signers

    if not os.path.isfile(source_path):
        raise SigningError("The document to sign was not found")
    if os.path.abspath(source_path) == os.path.abspath(output_path):
        raise SigningError(
            "The signed file must be written somewhere else, so the original "
            "stays as it is"
        )

    signer = _load_signer(certificate_path, password)

    field_spec = None
    if placement is not None:
        box = _pdf_box(placement, _page_height(source_path, placement.page))
        field_spec = fields.SigFieldSpec(
            sig_field_name=field_name,
            on_page=placement.page,
            box=box,
        )

    meta = signers.PdfSignatureMetadata(
        field_name=field_name,
        reason=reason or None,
        location=location or None,
        contact_info=contact or None,
    )

    pdf_signer = signers.PdfSigner(
        meta,
        signer=signer,
        stamp_style=_stamp_style(signer_label) if placement is not None else None,
        new_field_spec=field_spec,
    )

    try:
        with open(source_path, "rb") as source:
            writer = IncrementalPdfFileWriter(source)
            with open(output_path, "wb") as target:
                pdf_signer.sign_pdf(writer, output=target)
    except SigningError:
        raise
    except Exception as exc:
        logger.warning("Signing failed: %s", exc)
        _remove_partial(output_path)
        raise SigningError(_signing_message(exc)) from exc

    return {
        "output": output_path,
        "field_name": field_name,
        "visible": placement is not None,
        "signer": describe_certificate(certificate_path, password)["subject"],
        # Stated so no caller can quietly imply otherwise.
        "timestamped_by_authority": False,
        "revocation_info_embedded": False,
    }


def _load_signer(certificate_path: str, password: str):
    from pyhanko.sign import signers

    if not os.path.isfile(certificate_path):
        raise SigningError("The certificate file was not found")
    try:
        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=certificate_path,
            passphrase=(password or "").encode("utf-8"),
        )
    except Exception as exc:
        logger.info("PKCS#12 could not be opened: %s", exc)
        raise SigningError(
            "The certificate could not be opened. The password may be wrong, "
            "or the file may not be a PKCS#12 certificate."
        ) from exc
    if signer is None:
        raise SigningError(_PKCS12_REFUSED)
    return signer


def _signing_message(exc: Exception) -> str:
    text = str(exc).lower()
    if "encrypt" in text or "password" in text:
        return ("A document that is encrypted cannot be signed as it stands. "
                "Remove the password first, then sign.")
    if "field" in text and ("exist" in text or "duplicate" in text):
        return ("This document already has a signature field with that name. "
                "Choose another name.")
    return "The document could not be signed"


def _remove_partial(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        logger.info("A half-written signed file could not be removed: %s", path)


def verify_document(path: str,
                    trust_roots: Sequence[str] = ()) -> List[SignatureReport]:
    """Describe every signature in *path*.

    *trust_roots* are paths to certificates (PEM or DER) to treat as trusted.
    With none given, no signature can come back trusted, and each report says
    that in :attr:`SignatureReport.trust_problem` instead of leaving a bare
    "untrusted" for the caller to misread as "forged".
    """
    _require_pyhanko()
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.sign.validation.pdf_embedded import SignatureCoverageLevel
    from pyhanko_certvalidator import ValidationContext

    if not os.path.isfile(path):
        raise SigningError("The document was not found")

    roots = _load_roots(trust_roots)
    context = ValidationContext(trust_roots=roots, allow_fetching=False)

    reports: List[SignatureReport] = []
    try:
        with open(path, "rb") as handle:
            reader = PdfFileReader(handle)
            for embedded in reader.embedded_signatures:
                reports.append(_report(embedded, context, roots,
                                       validate_pdf_signature,
                                       SignatureCoverageLevel))
    except SigningError:
        raise
    except Exception as exc:
        logger.warning("Signature verification failed: %s", exc)
        raise SigningError("The document's signatures could not be read") from exc
    return reports


def _load_roots(trust_roots: Sequence[str]):
    from pyhanko_certvalidator.registry import SimpleCertificateStore  # noqa: F401
    from asn1crypto import pem, x509 as asn1_x509

    loaded = []
    for root in trust_roots or ():
        try:
            with open(root, "rb") as handle:
                data = handle.read()
            if pem.detect(data):
                for _, _, der in pem.unarmor(data, multiple=True):
                    loaded.append(asn1_x509.Certificate.load(der))
            else:
                loaded.append(asn1_x509.Certificate.load(data))
        except Exception as exc:
            logger.info("Trust root %s could not be read: %s", root, exc)
    return loaded


def _report(embedded, context, roots, validate, coverage_levels) -> SignatureReport:
    field_name = getattr(embedded, "field_name", "") or ""
    signer_name = _common_name(getattr(embedded, "signer_cert", None)) \
        if getattr(embedded, "signer_cert", None) is not None else ""

    notes: List[str] = []
    try:
        status = validate(embedded, signer_validation_context=context)
    except Exception as exc:
        logger.info("A signature could not be validated: %s", exc)
        return SignatureReport(
            field_name=field_name, signer=signer_name,
            intact=False, valid=False, trusted=False, covers_whole_file=False,
            trust_problem="This signature could not be checked at all",
            notes=["The signature is present but could not be read"],
        )

    covers = status.coverage == coverage_levels.ENTIRE_FILE
    if not covers:
        notes.append(
            "Something was added to the file after this signature was made; "
            "the signature covers only the part of the file up to that point"
        )
    if not roots:
        trust_problem = ("No trusted certificates were supplied, so nothing can "
                         "be said about who signed this")
    elif status.trusted:
        trust_problem = ""
    else:
        trust_problem = (str(status.trust_problem_indic)
                         if status.trust_problem_indic
                         else "The signer's certificate is not trusted here")

    notes.append("No trusted timestamp: the signing time is the one the signer "
                 "reported, not one a time authority confirmed")

    return SignatureReport(
        field_name=field_name,
        signer=signer_name,
        intact=bool(status.intact),
        valid=bool(status.valid),
        trusted=bool(status.trusted) if roots else False,
        covers_whole_file=bool(covers),
        signed_at=getattr(status, "signer_reported_dt", None),
        reason=_sig_string(embedded, "/Reason"),
        location=_sig_string(embedded, "/Location"),
        trust_problem=trust_problem,
        notes=notes,
    )


def _sig_string(embedded, key: str) -> str:
    try:
        value = embedded.sig_object.get(key)
        return str(value) if value else ""
    except Exception:
        return ""


def has_signatures(path: str) -> bool:
    """Whether the file carries any signature at all. Cheap, and never raises."""
    try:
        return bool(verify_document(path))
    except Exception:
        return False
