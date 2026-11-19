"""Create the self-signed PKCS#12 certificate the signing tests use.

This is a **test** identity and nothing else. It is self-signed, so no reader
anywhere will call a signature made with it trusted; what it is good for is
proving that the signing code produces a well-formed signature and that a later
change to the file is detected.

A real signature needs a certificate from a certificate authority the reader's
trust store knows. This script cannot make one and does not pretend to.

    python scripts/make_test_certificate.py

The file lands in tests/certificates/ and its password is TEST_PASSWORD below,
in the open, because it guards nothing.
"""
import datetime
import os
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

# Not a secret. The certificate it protects is a test fixture with no authority.
TEST_PASSWORD = "nextpdf-test"

FRIENDLY_NAME = "NextPDF Pro test signer"
COMMON_NAME = "NextPDF Pro Test Signer"
ORGANISATION = "NextPDF Pro (test only)"
VALID_YEARS = 10

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(HERE, "tests", "certificates")
P12_PATH = os.path.join(FOLDER, "test-signer.p12")
CERT_PATH = os.path.join(FOLDER, "test-signer.crt")


def build() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, COMMON_NAME),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORGANISATION),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "EG"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)  # self-signed: subject and issuer are the same
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365 * VALID_YEARS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        # A signing certificate must say it is one, or a validator rejects it
        # before it ever looks at the signature.
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,  # the old "non-repudiation" bit
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.ObjectIdentifier("1.2.840.113549.1.9.16.6.1")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    os.makedirs(FOLDER, exist_ok=True)
    bundle = pkcs12.serialize_key_and_certificates(
        name=FRIENDLY_NAME.encode("utf-8"),
        key=key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            TEST_PASSWORD.encode("utf-8")
        ),
    )
    with open(P12_PATH, "wb") as handle:
        handle.write(bundle)
    with open(CERT_PATH, "wb") as handle:
        handle.write(certificate.public_bytes(serialization.Encoding.PEM))

    print(f"wrote {P12_PATH}")
    print(f"wrote {CERT_PATH}")
    print(f"password: {TEST_PASSWORD} (a test fixture, not a secret)")
    print(f"valid until: {certificate.not_valid_after_utc:%Y-%m-%d}")


if __name__ == "__main__":
    build()
    sys.exit(0)
