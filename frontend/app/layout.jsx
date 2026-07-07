import "./globals.css";

export const metadata = {
  title: "SusBiome | Climate Risk Intelligence",
  description:
    "District-level flood, drought, and cyclone planning outlooks for Northeast India.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
