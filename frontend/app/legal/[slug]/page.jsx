import { notFound } from "next/navigation";
import AgriFooter from "../../../components/AgriFooter";
import AgriPageNav from "../../../components/AgriPageNav";
import { getLegalPage, legalPages } from "../../../lib/legalPages";

export function generateStaticParams() {
  return legalPages.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const page = getLegalPage(slug);

  if (!page) {
    return {
      title: "Legal | SusBiome",
    };
  }

  return {
    title: `${page.title} | SusBiome`,
    description: page.description,
  };
}

export default async function LegalPage({ params }) {
  const { slug } = await params;
  const page = getLegalPage(slug);

  if (!page) {
    notFound();
  }

  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section className="legal-section site-section subpage-section" aria-labelledby="legal-title">
        <div className="legal-shell">
          <div className="legal-heading">
            <p className="story-kicker">{page.kicker}</p>
            <h1 id="legal-title">{page.title}</h1>
            <p>{page.lead}</p>
            <span>Effective date: {page.updated}</span>
          </div>

          <article className="legal-document">
            {page.sections.map((section, index) => (
              <section key={`${section.heading || "section"}-${index}`}>
                {section.heading ? <h2>{section.heading}</h2> : null}
                {section.body?.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
                {section.bullets ? (
                  <ul>
                    {section.bullets.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </section>
            ))}
          </article>
        </div>
      </section>
      <AgriFooter />
    </main>
  );
}
