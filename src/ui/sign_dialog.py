#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dialogs for signing a document and for reading back its signatures.

The dialogs collect choices and present results.  Signing itself lives in
``src.engine.signing``, so the whole of this module can be tested without a
certificate and without writing a file.

One rule shapes every string here: a signature proves that the bytes under it
have not changed, and separately says who claims to have signed.  The second
part is only worth anything if the reader trusts the certificate.  The wording
never merges the two into a single tick.
"""

import logging
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QGroupBox, QComboBox, QSpinBox, QFileDialog,
    QTextBrowser, QWidget, QSizePolicy,
)

from src.i18n import get_translator

logger = logging.getLogger("NextPDF")

#: Unicode isolates. Text between them keeps its own direction instead of
#: taking the paragraph's, which matters wherever a run starts or ends with a
#: neutral character: ".p12" in an Arabic line otherwise renders as "p12.",
#: the dot having jumped to the other end. The same trick fixes the Android
#: page counter, where "1 / 7" came out as "7 / 1".
LTR_ISOLATE = "⁦"
POP_ISOLATE = "⁩"


def ltr(text: str) -> str:
    """*text* kept left-to-right however the line around it runs."""
    return f"{LTR_ISOLATE}{text}{POP_ISOLATE}"


def format_signing_time(moment, zone=None) -> str:
    """The signing time in local time, with its offset spelled out.

    The stamp drawn on the page carries local time; the value stored in the
    signature is UTC. Printing the stored value raw gave the report one clock
    and the page another for the same signature, which reads as a fault in a
    signature that is in fact sound. So both now say the same thing, and the
    offset is shown so the reader is never left guessing which zone it is.

    *zone* overrides the computer's own, which is what lets the formatting be
    tested at an offset the machine running the tests does not happen to be in.
    """
    if moment is None:
        return ""
    if moment.tzinfo is None:
        local = moment
    else:
        local = moment.astimezone(zone)
    text = local.strftime("%Y-%m-%d %H:%M:%S")
    offset = local.utcoffset()
    if offset is None:
        return text
    total_minutes = int(offset.total_seconds()) // 60
    sign = "-" if total_minutes < 0 else "+"
    hours, minutes = divmod(abs(total_minutes), 60)
    stamp = f"{sign}{hours:02d}" + (f":{minutes:02d}" if minutes else "")
    return f"{text} {stamp}"

#: Where a visible signature can be put, and the corner it is measured from.
POSITIONS = (
    ("bottom-right", "Bottom right"),
    ("bottom-left", "Bottom left"),
    ("top-right", "Top right"),
    ("top-left", "Top left"),
)

#: Default size of the drawn signature, in points (1/72 inch).
DEFAULT_WIDTH = 200
DEFAULT_HEIGHT = 64

#: Distance kept from the page edge, in points.
MARGIN = 36

#: Least width for the certificate path box, in pixels. It holds the longest
#: value on the form, so it is not left to share a row on equal terms.
CERTIFICATE_PATH_WIDTH = 280


def placement_rect(position, page_width, page_height,
                   width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, margin=MARGIN):
    """The rectangle for *position*, in the top-left origin the engine wants.

    Kept a plain function, and separate from the widgets, because getting a
    corner wrong is the kind of mistake that is invisible until someone looks
    at a signed page - so it is worth testing on its own.
    """
    width = min(float(width), max(float(page_width) - 2 * margin, 1.0))
    height = min(float(height), max(float(page_height) - 2 * margin, 1.0))
    left = margin if position.endswith("left") else page_width - margin - width
    top = margin if position.startswith("top") else page_height - margin - height
    left = max(0.0, float(left))
    top = max(0.0, float(top))
    return (left, top, left + width, top + height)


class SignDialog(QDialog):
    """Collects the certificate, the password and where the signature goes."""

    def __init__(self, parent=None, page_count=1, current_page=1,
                 suggested_name=""):
        super().__init__(parent)
        tr = get_translator().tr
        self.tr_ = tr
        self.page_count = max(1, int(page_count))
        self.setWindowTitle(tr("Sign with a certificate"))
        self.setModal(True)

        layout = QVBoxLayout(self)

        note = QLabel(tr(
            "A digital signature is added to a new copy of the file; this "
            "document is left as it is. The signature lets a reader prove the "
            "file has not changed since it was signed. Whether the reader also "
            "believes it was you depends on their trusting your certificate."))
        note.setWordWrap(True)
        layout.addWidget(note)

        certificate_box = QGroupBox(tr("Certificate"))
        certificate_form = QFormLayout(certificate_box)
        picker = self.certificate_row = QWidget()
        # Without this the row is only as wide as it needs to be, so the path
        # box keeps its minimum while the plain text fields below stretch.
        picker.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Preferred)
        picker_row = QHBoxLayout(picker)
        picker_row.setContentsMargins(0, 0, 0, 0)
        self.certificate_path = QLineEdit()
        self.certificate_path.setObjectName("certificate_path")
        # The longest value in this dialog is a file path, so it gets the most
        # room rather than the least: the label is short and the extensions
        # moved into the placeholder, where they are also isolated so the dot
        # stays in front of the extension in an Arabic layout.
        self.certificate_path.setPlaceholderText(ltr(".p12 / .pfx"))
        self.certificate_path.setMinimumWidth(CERTIFICATE_PATH_WIDTH)
        self.browse_button = QPushButton(tr("Browse"))
        self.browse_button.clicked.connect(self._browse)
        # The path box asks for a minimum of its own, so while the dialog is
        # briefly narrower than the two of them together the layout has to take
        # the difference out of one. Left alone it takes it out of the button
        # and clips the label; pinning the button at the width of its own text
        # sends the squeeze to the path box, where text scrolls instead of
        # disappearing.
        picker_row.addWidget(self.certificate_path, 1)
        picker_row.addWidget(self.browse_button, 0)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setObjectName("certificate_password")
        certificate_form.addRow(tr("Certificate file"), picker)
        certificate_form.addRow(tr("Certificate password"), self.password)
        self.check_button = QPushButton(tr("Check the certificate"))
        self.check_button.clicked.connect(self._check_certificate)
        certificate_form.addRow("", self.check_button)
        self.certificate_details = QLabel("")
        self.certificate_details.setWordWrap(True)
        self.certificate_details.setObjectName("certificate_details")
        # A wrapped label in a form row is given the height of the text it
        # held when the dialog was laid out, so a longer message - the wrong
        # password one, say - was cut off mid-sentence with nothing to scroll.
        details_policy = QSizePolicy(QSizePolicy.Policy.Preferred,
                                     QSizePolicy.Policy.MinimumExpanding)
        details_policy.setHeightForWidth(True)
        self.certificate_details.setSizePolicy(details_policy)
        certificate_form.addRow(self.certificate_details)
        layout.addWidget(certificate_box)

        reason_box = QGroupBox(tr("What the signature records"))
        reason_form = QFormLayout(reason_box)
        self.signer_label = QLineEdit(suggested_name)
        self.reason = QLineEdit()
        self.location = QLineEdit()
        reason_form.addRow(tr("Name to show"), self.signer_label)
        reason_form.addRow(tr("Reason"), self.reason)
        reason_form.addRow(tr("Place"), self.location)
        layout.addWidget(reason_box)

        appearance_box = QGroupBox(tr("Appearance"))
        appearance_layout = QVBoxLayout(appearance_box)
        self.visible = QCheckBox(tr("Draw the signature on the page"))
        self.visible.setObjectName("signature_visible")
        self.visible.setChecked(True)
        self.visible.toggled.connect(self._on_visible_toggled)
        appearance_layout.addWidget(self.visible)
        invisible_note = QLabel(tr(
            "An invisible signature is not a weaker one. It is simply not drawn."))
        invisible_note.setWordWrap(True)
        appearance_layout.addWidget(invisible_note)
        placement_form = QFormLayout()
        self.page = QSpinBox()
        self.page.setRange(1, self.page_count)
        self.page.setValue(min(max(1, int(current_page)), self.page_count))
        self.position = QComboBox()
        for key, caption in POSITIONS:
            self.position.addItem(tr(caption), key)
        placement_form.addRow(tr("Page"), self.page)
        placement_form.addRow(tr("Position"), self.position)
        appearance_layout.addLayout(placement_form)
        layout.addWidget(appearance_box)

        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setObjectName("sign_message")
        layout.addWidget(self.message)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton(tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.sign_button = QPushButton(tr("Sign"))
        self.sign_button.setDefault(True)
        self.sign_button.clicked.connect(self._on_sign)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.sign_button)
        layout.addLayout(buttons)

    # ------------------------------------------------------------ behaviour
    def _on_visible_toggled(self, checked):
        self.page.setEnabled(checked)
        self.position.setEnabled(checked)

    def _show_details(self, text):
        """Put *text* under the certificate row and make room for it.

        Without the resize the dialog keeps the height it was laid out with,
        and anything longer than the first message is simply clipped.
        """
        label = self.certificate_details
        label.setText(text)
        # A size policy that honours heightForWidth is not enough on its own:
        # the row keeps whatever height it already had until something asks
        # for more. Asking explicitly is what stops the text being cut.
        width = label.width() or label.sizeHint().width()
        label.setMinimumHeight(label.heightForWidth(width) if text else 0)
        label.updateGeometry()
        # adjustSize() would also pull the width back to the hint, throwing
        # away any width the reader had given the dialog and reflowing the
        # certificate row on the way - which is where the Browse button was
        # seen squeezed and its label cut. Only the height needs to change.
        self.resize(max(self.width(), self.sizeHint().width()),
                    self.sizeHint().height())

    def _browse(self):
        tr = self.tr_
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose a certificate"), "",
            f"{tr('Certificate files')} (*.p12 *.pfx)")
        if path:
            self.certificate_path.setText(path)
            self._show_details("")

    def _check_certificate(self):
        """Read the certificate now, so a wrong password is caught here."""
        from src.engine.signing import SigningError, describe_certificate

        tr = self.tr_
        path = self.certificate_path.text().strip()
        if not path:
            self._show_details(tr("Choose a certificate file first."))
            return
        try:
            details = describe_certificate(path, self.password.text())
        except SigningError as error:
            # The engine raises its message in English, which is this
            # project's translation key, so it is translated here rather
            # than shown raw in the middle of an Arabic dialog.
            self._show_details(tr(str(error)))
            return
        lines = [f"{tr('Signer')}: {details['subject']}",
                 f"{tr('Issued by')}: {details['issuer']}"]
        if details["valid_until"]:
            # Isolated for the same reason as the extensions: the hyphens are
            # neutral, so "2036-11-16" was being drawn as "16-11-2036" - a
            # different, plausible-looking date rather than obvious nonsense.
            lines.append(f"{tr('Valid until')}: "
                         f"{ltr(details['valid_until'].strftime('%Y-%m-%d'))}")
        if details["expired"]:
            lines.append(tr("This certificate has expired."))
        if details["self_signed"]:
            lines.append(tr(
                "This certificate signed itself, so no authority vouches for "
                "it. A signature made with it still proves the file has not "
                "changed, but a reader has no way to confirm who made it "
                "unless you give them this certificate yourself."))
        self._show_details("\n".join(lines))

    def validation_error(self):
        """The reason the signature cannot be made, or None."""
        tr = self.tr_
        path = self.certificate_path.text().strip()
        if not path:
            return tr("Choose the certificate to sign with.")
        if not os.path.isfile(path):
            return tr("That certificate file does not exist.")
        return None

    def _on_sign(self):
        error = self.validation_error()
        if error:
            self.message.setText(error)
            return
        self.accept()

    # --------------------------------------------------------------- result
    def signing_arguments(self) -> dict:
        """What the window needs: the engine's keywords, minus the placement.

        The placement needs the page's size, which the window has and the
        dialog does not, so the corner is handed over unresolved.
        """
        return {
            "certificate_path": self.certificate_path.text().strip(),
            "password": self.password.text(),
            "reason": self.reason.text().strip(),
            "location": self.location.text().strip(),
            "signer_label": self.signer_label.text().strip(),
            "visible": self.visible.isChecked(),
            "page": self.page.value(),
            "position": self.position.currentData(),
        }


def report_text(reports, tr) -> str:
    """Turn verification reports into plain sentences.

    Separated from the widget so the wording itself can be tested - it is the
    part a reader will act on, and the part easiest to get subtly wrong.
    """
    if not reports:
        return tr("This document has no digital signature.")
    blocks = []
    for index, report in enumerate(reports, start=1):
        lines = [f"<b>{tr('Signature')} {index}</b>"]
        lines.append(f"{tr('Signer')}: {report.signer or tr('not stated')}")
        if report.signed_at:
            lines.append(f"{tr('Signed at')}: "
                         f"{ltr(format_signing_time(report.signed_at))} "
                         f"({tr('the time the signer claims, not a verified one')})")
        if report.unchanged_since_signing:
            lines.append(tr("The file has not changed since it was signed."))
        else:
            lines.append(tr("The file HAS changed since it was signed."))
        if not report.covers_whole_file:
            lines.append(tr("Something was added to the file after signing; "
                            "the signature does not cover that part."))
        if report.trusted:
            lines.append(tr("The certificate is trusted on this computer."))
        else:
            lines.append(tr("The signer is not confirmed: no authority this "
                            "computer trusts vouches for the certificate."))
            if report.trust_problem:
                # Not "Reason": that word is two lines below for the reason
                # the signer typed, and one word for two different things in
                # the same short report is how a reader ends up misreading it.
                lines.append(f"{tr('Why the signer is not confirmed')}: "
                             f"{tr(report.trust_problem)}")
        if report.reason:
            lines.append(f"{tr('Reason given')}: {report.reason}")
        if report.location:
            lines.append(f"{tr('Place given')}: {report.location}")
        for note in report.notes:
            # The engine writes its notes in English, which is the translation
            # key here; anything it passes through from pyHanko has no entry
            # and falls back to the key, so it stays readable either way.
            lines.append(f"• {tr(note)}")
        blocks.append("<br>".join(lines))
    return "<br><br>".join(blocks)


class SignatureReportDialog(QDialog):
    """Shows what each signature in a document does and does not prove."""

    def __init__(self, reports, parent=None):
        super().__init__(parent)
        tr = get_translator().tr
        self.setWindowTitle(tr("Check the signatures"))
        self.setModal(True)
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        view = QTextBrowser()
        view.setObjectName("signature_report")
        view.setHtml(report_text(reports, tr))
        layout.addWidget(view)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)
