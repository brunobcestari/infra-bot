"""QR code generation utilities for TOTP enrollment."""

from io import BytesIO
import qrcode


def generate_qr_code(data: str) -> BytesIO:
    """Generate QR code as PNG image buffer.

    Args:
        data: Data to encode in QR code (typically otpauth:// URI)

    Returns:
        BytesIO buffer containing PNG image data
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_qr_code_ascii(data: str) -> str:
    """Generate ASCII art QR code for terminal display.

    Args:
        data: Data to encode in QR code (typically otpauth:// URI)

    Returns:
        ASCII art representation of QR code
    """
    qr = qrcode.QRCode(border=2)
    qr.add_data(data)
    qr.make(fit=True)

    # Use print_ascii() to get string representation
    import io
    buffer = io.StringIO()
    qr.print_ascii(out=buffer)
    return buffer.getvalue()
