import Image from "next/image";
import Link from "next/link";
import guideBlocks from "../../../lib/leihaaoGuide.json";

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

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function GuideBlock({ block, index }) {
  if (block.type === "section") {
    return (
      <h2 id={slugify(block.text)} className="leihaao-section-title">
        <span>{String(index + 1).padStart(2, "0")}</span>
        {block.text}
      </h2>
    );
  }

  if (block.type === "subheading") {
    return <h3>{block.text}</h3>;
  }

  if (block.type === "paragraph") {
    return <p>{block.text}</p>;
  }

  if (block.type === "list") {
    const ListTag = block.ordered ? "ol" : "ul";
    const listClass = block.level ? "leihaao-list leihaao-list--nested" : "leihaao-list";
    return (
      <ListTag className={listClass} start={block.start}>
        {block.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ListTag>
    );
  }

  if (block.type === "table") {
    return (
      <div className="leihaao-table-wrap" tabIndex="0" role="region" aria-label="Scrollable guide table">
        <table>
          <thead>
            <tr>
              {block.headers.map((header) => (
                <th key={header} scope="col">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={`${row[0]}-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`${cellIndex}-${cell}`}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === "image") {
    return (
      <figure className="leihaao-figure">
        <Image
          src={block.src}
          alt={block.alt}
          width={1344}
          height={block.src.endsWith("-1.png") ? 466 : 608}
          sizes="(max-width: 760px) 92vw, 1040px"
          quality={100}
          unoptimized
        />
      </figure>
    );
  }

  return null;
}

export default function LeihaaoGuidePage() {
  const title = guideBlocks.find((block) => block.type === "title");
  const subtitle = guideBlocks.find((block) => block.type === "subtitle");
  const meta = guideBlocks.find((block) => block.type === "meta");
  const content = guideBlocks.filter(
    (block) => !["title", "subtitle", "meta"].includes(block.type),
  );
  const sections = content.filter((block) => block.type === "section");
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

      <nav className="leihaao-index" aria-label="Guide sections">
        <p>In this guide</p>
        <div>
          {sections.map((section, index) => (
            <a href={`#${slugify(section.text)}`} key={section.text}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {section.text}
            </a>
          ))}
        </div>
      </nav>

      <article className="leihaao-content">
        {content.map((block, index) => {
          const sectionIndex =
            content.slice(0, index + 1).filter((item) => item.type === "section").length - 1;
          return <GuideBlock block={block} index={sectionIndex} key={`${block.type}-${index}`} />;
        })}
      </article>

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
