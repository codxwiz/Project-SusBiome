import Image from "next/image";
import Link from "next/link";

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function GuideBlock({ block, sectionNumber }) {
  if (block.type === "section") {
    return (
      <h2 id={slugify(block.text)} className="leihaao-section-title">
        <span>{String(sectionNumber).padStart(2, "0")}</span>
        {block.text}
      </h2>
    );
  }

  if (block.type === "subheading") return <h3>{block.text}</h3>;
  if (block.type === "paragraph") return <p>{block.text}</p>;

  if (block.type === "list") {
    const ListTag = block.ordered ? "ol" : "ul";
    const listClass = block.level ? "leihaao-list leihaao-list--nested" : "leihaao-list";
    return (
      <ListTag className={listClass} start={block.start}>
        {block.items.map((item) => <li key={item}>{item}</li>)}
      </ListTag>
    );
  }

  if (block.type === "table") {
    return (
      <div className="leihaao-table-wrap" tabIndex="0" role="region" aria-label="Scrollable guide table">
        <table>
          <thead>
            <tr>{block.headers.map((header) => <th key={header} scope="col">{header}</th>)}</tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={`${row[0]}-${rowIndex}`}>
                {row.map((cell, cellIndex) => <td key={`${cellIndex}-${cell}`}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="leihaao-scroll-cue" aria-hidden="true" />
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

function splitIntoParts(blocks) {
  const chapters = [];
  let chapter = [];

  blocks.forEach((block) => {
    if (block.type === "section" && chapter.length) {
      chapters.push(chapter);
      chapter = [];
    }
    chapter.push(block);
  });
  if (chapter.length) chapters.push(chapter);

  return [chapters.slice(0, 3).flat(), chapters.slice(3, 5).flat(), chapters.slice(5).flat()];
}

const PART_LABELS = ["Plant care essentials", "Diagnosis & remedies", "Protection & routine care"];

export default function GuideReader({ content, activePart }) {
  const parts = splitIntoParts(content);

  const precedingSectionCount = content
    .slice(0, content.indexOf(parts[activePart][0]))
    .filter((block) => block.type === "section").length;

  return (
    <section id="guide-reader" className="leihaao-reader" aria-label="Plant care guide reader">
      <nav className="leihaao-parts" aria-label="Guide parts">
        {PART_LABELS.map((label, index) => (
          <Link
            key={label}
            href={`?part=${index + 1}#guide-reader`}
            className={index === activePart ? "is-active" : ""}
            aria-current={index === activePart ? "step" : undefined}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            {label}
          </Link>
        ))}
      </nav>

      <div className="leihaao-part-status">
        <span>Part {activePart + 1} of {parts.length}</span>
        <div aria-hidden="true"><i style={{ width: `${((activePart + 1) / parts.length) * 100}%` }} /></div>
      </div>

      <article className="leihaao-content">
        {parts[activePart].map((block, index) => {
          const sectionNumber = precedingSectionCount + parts[activePart]
            .slice(0, index + 1)
            .filter((item) => item.type === "section").length;
          return <GuideBlock block={block} sectionNumber={sectionNumber} key={`${block.type}-${index}`} />;
        })}
      </article>

      <nav className="leihaao-page-actions" aria-label="Guide pagination">
        {activePart > 0 && (
          <Link className="leihaao-page-button leihaao-page-button--back" href={`?part=${activePart}#guide-reader`}>
            Back
          </Link>
        )}
        {activePart < parts.length - 1 ? (
          <Link className="leihaao-page-button" href={`?part=${activePart + 2}#guide-reader`}>
            Next <span aria-hidden="true">→</span>
          </Link>
        ) : (
          <p className="leihaao-complete">Guide complete</p>
        )}
      </nav>
    </section>
  );
}
