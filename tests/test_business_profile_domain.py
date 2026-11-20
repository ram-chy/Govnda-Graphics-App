"""Approved domain rules for the single business profile."""

from __future__ import annotations

from dataclasses import replace

from app.domain.business_logo import (
    ALLOWED_LOGO_EXTENSIONS,
    MAX_LOGO_BYTES,
    PNG_SIGNATURE,
    validate_logo_content,
)
from app.domain.business_profile import (
    BusinessProfile,
    ProfileStatus,
    ProfileVersion,
    assess_completion,
    validate_profile,
)


def _complete_profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Gobindas Graphics",
        address="Sector 1",
        phone="9876543210",
        email="office@example.com",
        footer_message="Thank you",
        logo_reference="Logos/logo.png",
    )


def test_all_mandatory_text_fields_and_logo_are_required() -> None:
    result = validate_profile(_complete_profile())

    assert result.is_valid
    assert result.errors == {}
    assert validate_profile(BusinessProfile()).errors == {
        "business_name": "Business name is required.",
        "address": "Address is required.",
        "phone": "Phone is required.",
        "email": "Email is required.",
        "footer_message": "Footer message is required.",
        "logo": "A business logo is required.",
    }


def test_empty_or_whitespace_mandatory_text_is_rejected() -> None:
    for name in ("", "   "):
        result = validate_profile(replace(_complete_profile(), business_name=name))

        assert not result.is_valid
        assert result.errors == {"business_name": "Business name is required."}


def test_optional_fields_are_not_required() -> None:
    profile = _complete_profile()

    assert profile.secondary_phone == ""
    assert profile.website == ""
    assert profile.registration_number == ""
    assert validate_profile(profile).is_valid


def test_no_phone_or_email_format_rules_are_applied() -> None:
    profile = replace(
        _complete_profile(), phone="not-a-phone", email="not-an-email"
    )

    assert validate_profile(profile).is_valid


def test_normalization_trims_all_stored_text() -> None:
    profile = BusinessProfile(
        business_name="  Gobindas Graphics  ",
        address=" Sector 1 ",
        footer_message="  Thank you  ",
    )

    normalized = profile.normalized()

    assert normalized.business_name == "Gobindas Graphics"
    assert normalized.address == "Sector 1"
    assert normalized.footer_message == "Thank you"


def test_completion_lists_every_missing_required_field() -> None:
    empty = assess_completion(None)
    incomplete = assess_completion(BusinessProfile())
    complete = assess_completion(_complete_profile())

    assert empty.status is ProfileStatus.EMPTY
    assert empty.missing_fields == (
        "business_name",
        "address",
        "phone",
        "email",
        "footer_message",
        "logo",
    )
    assert incomplete.status is ProfileStatus.INCOMPLETE
    assert complete.status is ProfileStatus.COMPLETE
    assert complete.missing_fields == ()
    assert "No business profile yet" in empty.label
    assert "Business name" in incomplete.label
    assert "Logo" in incomplete.label
    assert complete.label == "Complete"


def test_history_snapshot_round_trips_to_a_profile() -> None:
    version = ProfileVersion(
        version_number=7,
        business_name="Gobindas Graphics",
        address="Sector 1",
        phone="9876543210",
        secondary_phone="",
        email="office@example.com",
        website="example.com",
        registration_number="REG-1",
        footer_message="Thank you",
        logo_reference="Logos/logo.png",
        created_at="now",
        updated_at="now",
    )

    assert version.to_profile() == BusinessProfile(
        business_name="Gobindas Graphics",
        address="Sector 1",
        phone="9876543210",
        email="office@example.com",
        website="example.com",
        registration_number="REG-1",
        footer_message="Thank you",
        logo_reference="Logos/logo.png",
        version_number=7,
    )


def test_logo_content_rules_accept_valid_png_and_jpeg() -> None:
    png_header = PNG_SIGNATURE + b"\x00\x00\x00\rIHDR"
    png = validate_logo_content(
        source_name="logo.PNG",
        size_bytes=100,
        header=png_header,
        tail=b"",
    )
    jpeg = validate_logo_content(
        source_name="logo.jpeg",
        size_bytes=100,
        header=b"\xff\xd8\xff\xe0",
        tail=b"\xff\xd9",
    )

    assert png.is_valid
    assert png.media_type == ALLOWED_LOGO_EXTENSIONS[".png"]
    assert jpeg.is_valid
    assert jpeg.media_type == ALLOWED_LOGO_EXTENSIONS[".jpeg"]


def test_logo_content_rules_reject_unsafe_or_invalid_files() -> None:
    invalid_extension = validate_logo_content(
        source_name="logo.gif", size_bytes=10, header=b"GIF89a", tail=b""
    )
    empty = validate_logo_content(
        source_name="logo.png", size_bytes=0, header=b"", tail=b""
    )
    oversized = validate_logo_content(
        source_name="logo.png",
        size_bytes=MAX_LOGO_BYTES + 1,
        header=PNG_SIGNATURE + b"\x00\x00\x00\rIHDR",
        tail=b"",
    )
    wrong_content = validate_logo_content(
        source_name="logo.png", size_bytes=100, header=b"not-a-png", tail=b""
    )

    assert "PNG, JPG" in invalid_extension.errors["logo"]
    assert "empty" in empty.errors["logo"]
    assert "5 MB" in oversized.errors["logo"]
    assert "not a valid PNG" in wrong_content.errors["logo"]
