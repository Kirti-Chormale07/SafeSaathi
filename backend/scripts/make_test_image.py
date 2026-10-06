"""Create a fake scam SMS screenshot for end-to-end OCR testing."""
from PIL import Image, ImageDraw, ImageFont

W, H = 900, 320
img = Image.new("RGB", (W, H), "#f6f7f9")
d = ImageDraw.Draw(img)

# message bubble
d.rounded_rectangle([30, 30, W - 30, H - 30], radius=18, fill="#ffffff", outline="#d0d5dd", width=2)

try:
    font = ImageFont.truetype("arial.ttf", 26)
    small = ImageFont.truetype("arial.ttf", 20)
except Exception:
    font = ImageFont.load_default(size=26)
    small = ImageFont.load_default(size=20)

lines = [
    "URGENT: Your bank account will be BLOCKED in 2 hours.",
    "KYC expired. Update now - click http://sbi-kyc-verify.xyz",
    "and share OTP 998877 to avoid freeze.",
    "",
    "- Bank Security Team",
]
y = 60
for i, line in enumerate(lines):
    d.text((60, y), line, fill="#111827" if i < 4 else "#6b7280", font=font if i < 4 else small)
    y += 44

img.save(r"C:\Users\Kirti\SafeSaathi\backend\test_scam.png")
print("saved test_scam.png")
