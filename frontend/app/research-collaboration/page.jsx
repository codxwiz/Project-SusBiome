import Link from "next/link";
import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";

export const metadata = {
  title: "Research Collaboration | SusBiome",
  description:
    "Research collaboration with SusBiome across smallholder farms, institutional agricultural programmes, and climate-resilient farming systems.",
};

export default function ResearchCollaborationPage() {
  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section
        id="research"
        className="research-section site-section subpage-section"
        aria-labelledby="research-title"
      >
        <div className="section-copy section-copy--wide research-intro">
          <p className="story-kicker">Research collaboration</p>
          <h1 id="research-title">Research that stays accountable to the field.</h1>
          <p>
            At SusBiome, we believe meaningful agricultural innovation happens through
            collaboration. We actively partner with research institutions, universities,
            development organizations, government agencies, startups, and industry leaders to
            generate practical, field-driven solutions for climate-resilient and sustainable
            agriculture.
          </p>
        </div>

        <div className="research-collab-grid" aria-label="Research collaboration focus areas">
          <article>
            <span>01</span>
            <h2>Field Trials and Product Demonstrations</h2>
          </article>
          <article>
            <span>02</span>
            <h2>Agricultural Surveys and Baseline Assessments</h2>
          </article>
          <article>
            <span>03</span>
            <h2>Climate Adaptation and Resilience Projects</h2>
          </article>
          <article>
            <span>04</span>
            <h2>Participatory Rural and Community-Based Studies</h2>
          </article>
          <article>
            <span>05</span>
            <h2>Climate Vulnerability and Risk Studies</h2>
          </article>
        </div>

        <Link className="research-cta" href="/contact">
          Reach out for more on research collaboration
        </Link>
      </section>
      <AgriFooter />
    </main>
  );
}
