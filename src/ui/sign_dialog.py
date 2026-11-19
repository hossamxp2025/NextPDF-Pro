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
    QTextBrowser, QWidget,
)

from src.i18n import get_translator

logger = logging.getLogger("NextPDF")

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
        picker = QWidget()
        picker_row = QHBoxLayout(picker)
        picker_row.setContentsMargins(0, 0, 0, 0)
        self.certificate_path = QLineEdit()
        self.certificate_path.setObjectName("certificate_path")
        self.browse_button = QPushButton(tr("Browse"))
        self.browse_button.clicked.connect(self._browse)
        picker_row.addWidget(self.certificate_path)
        picker_row.addWidget(self.browse_button)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setObjectName("certificate_password")
        certificate_form.addRow(tr("Certificate file (.p12 or .pfx)"), picker)
        certificate_form.addRow(tr("Certificate password"), self.password)
        self.check_button = QPushButton(tr("Check the certificate"))
        self.check_button.clicked.connect(self._check_certificate)
        certificate_form.addRow("", self.check_button)
        self.certificate_details = QLabel("")
        self.certificate_details.setWordWrap(True)
        self.certificate_details.setObjectName("certificate_details")
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

    def _browse(self):
        tr = self.tr_
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose a certificate"), "",
            f"{tr('Certificate files')} (*.p12 *.pfx)")
        if path:
            self.certificate_path.setText(path)
            self.certificate_details.setText("")

    def _check_certificate(self):
        """Read the certificate now, so a wrong password is caught here."""
        from src.engine.signing import SigningError, describe_certificate

        tr = self.tr_
        path = self.certificate_path.text().strip()
        if not path:
            self.certificate_details.setText(tr("Choose a certificate file first."))
            return
        try:
            details = describe_certificate(path, self.password.text())
        except SigningError as error:
            self.certificate_details.setText(str(error))
            return
        lines = [f"{tr('Signer')}: {details['subject']}",
                 f"{tr('Issued by')}: {details['issuer']}"]
        if details["valid_until"]:
            lines.append(f"{tr('Valid until')}: "
                         f"{details['valid_until'].strftime('%Y-%m-%d')}")
        if details["expired"]:
            lines.append(tr("This certificate has expired."))
        if details["self_signed"]:
            lines.append(tr(
                "This certificate signed itself, so no authority vouches for "
                "it. A signature made with it still proves the file has not "
                "changed, but a reader has no way to confirm who made it "
                "unless you give them this certificate yourself."))
        self.certificate_details.setText("\n".join(lines))

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
                         f"{report.signed_at.strftime('%Y-%m-%d %H:%M')} "
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
                lines.append(f"{tr('Reason')}: {report.trust_problem}")
        if report.reason:
            lines.append(f"{tr('Reason given')}: {report.reason}")
        if report.location:
            lines.append(f"{tr('Place given')}: {report.location}")
        for note in report.notes:
            lines.append(f"• {note}")
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
