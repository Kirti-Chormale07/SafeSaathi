import "./globals.css";
import SWRegister from "@/components/SWRegister";

export const metadata = {
  title: "SafeSaathi - AI Scam Guardian",
  description:
    "Paste, screenshot or speak a suspicious message. SafeSaathi explains the scam in Hindi, Marathi or English and tells you what to do next.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "SafeSaathi" },
};

export const viewport = {
  themeColor: "#0f766e",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <SWRegister />
        {children}
      </body>
    </html>
  );
}
