import Image from "next/image";
import Link from "next/link";
import guideBlocks from "../../../lib/leihaaoGuide.json";
import GuideReader from "./GuideReader";

export const metadata = {
  title: "Leihaao Plant Care Guide | SusBiome",
  description:
    "Leaf colour chart, feeding doses and natural plant protection for home and rooftop gardeners.",
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
};

const DOWNLOAD_PATH = "/downloads/Leihaao_Plant_Care_Guide.docx";

export default async function LeihaaoGuidePage({ searchParams }) {
  const params = await searchParams;
  const requestedPart = Number.parseInt(params?.part ?? "1", 10);
  const activePart = Number.isFinite(requestedPart)
    ? Math.min(3, Math.max(1, requestedPart)) - 1
    : 0;
  const title = guideBlocks.find((block) => block.type === "title");
  const subtitle = guideBlocks.find((block) => block.type === "subtitle");
  const meta = guideBlocks.find((block) => block.type === "meta");
  const content = guideBlocks.filter(
    (block) => !["title", "subtitle", "meta"].includes(block.type),
  );
  return (
    <main className="leihaao-guide">
      <header className="leihaao-header">
        <Link href="/" aria-label="SusBiome home">
          <Image
            src="/images/susbiome-logo.png"
            alt="SusBiome"
            width={74}
            height={60}
            priority
            quality={100}
            unoptimized
          />
        </Link>
        <a className="leihaao-download leihaao-download--header" href={DOWNLOAD_PATH} download>
          <span aria-hidden="true">↓</span>
          Download
        </a>
      </header>

      <section className="leihaao-intro" aria-labelledby="leihaao-title">
        <h1 id="leihaao-title">{title.text}</h1>
        <p className="leihaao-subtitle">{subtitle.text}</p>
        <p className="leihaao-meta">{meta.text}</p>
      </section>

      <GuideReader content={content} activePart={activePart} />

      <section className="leihaao-closing" aria-label="Download the guide">
        <p>Keep the complete guide available offline.</p>
        <a className="leihaao-download leihaao-download--light" href={DOWNLOAD_PATH} download>
          <span aria-hidden="true">↓</span>
          Download
        </a>
      </section>

      <footer className="leihaao-footer">©2026 SusBiome. All rights reserved.</footer>
    </main>
  );
}
