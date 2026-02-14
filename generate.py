#!/usr/bin/env python3
"""
Business Card Website Generator
Generates a static HTML contact card from a JSON business card file with an embedded vCard QR code.
"""

import json
import base64
import re
import sys
from pathlib import Path
from io import BytesIO
from urllib.parse import quote

try:
    import qrcode
    from PIL import Image
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("Error: Required packages not found. Install with: pip install -r requirements.txt")
    sys.exit(1)


def load_business_card(json_path):
    """Load business card data from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        sys.exit(1)


def generate_vcard(data):
    """
    Generate vCard format string from business card data.
    Uses vCard 3.0 format for maximum compatibility.
    """
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
    ]

    # Full Name (required)
    name = data.get('name', 'Unknown')
    lines.append(f"FN:{escape_vcard(name)}")

    # Structured Name
    lines.append(f"N:{escape_vcard(name)};;;")

    # Title
    if data.get('title'):
        lines.append(f"TITLE:{escape_vcard(data['title'])}")

    # Organization
    if data.get('company'):
        lines.append(f"ORG:{escape_vcard(data['company'])}")

    # Phone
    if data.get('phone'):
        lines.append(f"TEL;TYPE=WORK:{escape_vcard(data['phone'])}")

    # Email
    if data.get('email'):
        lines.append(f"EMAIL;TYPE=INTERNET:{escape_vcard(data['email'])}")

    # Website
    if data.get('website'):
        lines.append(f"URL:{escape_vcard(data['website'])}")

    # Social Media as URLs with X-properties (custom fields)
    if data.get('linkedin'):
        lines.append(f"URL;X-LABEL=LinkedIn:{escape_vcard(data['linkedin'])}")

    if data.get('github'):
        lines.append(f"URL;X-LABEL=GitHub:{escape_vcard(data['github'])}")

    if data.get('twitter'):
        lines.append(f"URL;X-LABEL=Twitter:{escape_vcard(data['twitter'])}")

    lines.append("END:VCARD")
    return "\n".join(lines)


def escape_vcard(text):
    """Escape special characters in vCard fields."""
    if not text:
        return ""
    # Escape semicolons and commas in vCard format
    text = str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return text


def generate_qr_code(vcard_data):
    """
    Generate QR code from vCard data and return as base64 data URI.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(vcard_data)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Return as data URI
    return f"data:image/png;base64,{img_str}"


def render_template(template_path, output_path, card_data, qr_code_uri):
    """
    Render the HTML template with card data and QR code.
    """
    env = Environment(loader=FileSystemLoader(template_path.parent))
    template = env.get_template(template_path.name)

    html_content = template.render(
        name=card_data.get('name', 'Unknown'),
        title=card_data.get('title'),
        company=card_data.get('company'),
        email=card_data.get('email'),
        phone=card_data.get('phone'),
        website=card_data.get('website'),
        linkedin=card_data.get('linkedin'),
        github=card_data.get('github'),
        twitter=card_data.get('twitter'),
        qr_code=qr_code_uri,
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def slugify_name(value):
    """Normalize a string for use as a filename."""
    if not value:
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9 _]+", "", text)
    text = text.replace(" ", "_")
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def choose_output_path(output_dir, base_name):
    """Choose a non-colliding output path using numeric suffixes."""
    output_path = output_dir / f"{base_name}.html"
    if not output_path.exists():
        return output_path

    index = 2
    while True:
        candidate = output_dir / f"{base_name}-{index}.html"
        if not candidate.exists():
            return candidate
        index += 1


def main():
    """Main entry point."""
    # Define paths
    project_root = Path(__file__).parent
    input_dir = project_root / "input"
    template_path = project_root / "templates" / "card.html"
    output_dir = project_root / "output"

    print("🎴 Business Card Generator")
    print("-" * 50)

    json_paths = sorted(input_dir.glob("*.json"))
    if not json_paths:
        print(f"Error: No JSON files found in {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Found {len(json_paths)} JSON file(s) in: {input_dir}")

    for json_path in json_paths:
        print("-" * 50)
        print(f"📖 Loading business card data from: {json_path}")
        card_data = load_business_card(json_path)
        print(f"   ✓ Loaded card for: {card_data.get('name', 'Unknown')}")

        base_name = slugify_name(card_data.get('name', ''))
        if not base_name:
            base_name = slugify_name(json_path.stem)
        if not base_name:
            base_name = "card"

        output_path = choose_output_path(output_dir, base_name)

        # Generate vCard
        print("📝 Generating vCard format...")
        vcard = generate_vcard(card_data)
        print("   ✓ vCard generated")

        # Generate QR code
        print("📊 Generating QR code...")
        qr_code_uri = generate_qr_code(vcard)
        print("   ✓ QR code created (embedded as data URI)")

        # Render template
        print("🎨 Rendering HTML template...")
        render_template(template_path, output_path, card_data, qr_code_uri)
        print("   ✓ Template rendered")
        print(f"✅ Success! Website generated at: {output_path}")

    print("-" * 50)
    print("✅ Done! Open the generated HTML file(s) in a web browser.")


if __name__ == "__main__":
    main()
