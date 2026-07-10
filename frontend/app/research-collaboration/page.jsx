import Link from "next/link";
import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";

export const metadata = {
  title: "Research & Collaboration | SusBiome",
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
          <p className="story-kicker">Research & collaboration</p>
          <h1 id="research-title">Research that stays accountable to the field.</h1>
          <p>
            We work across scales- from smallholder farms to institutional agricultural programmes
            designing, implementing, and evaluating farming systems built for the realities of climate
            change and economic pressure.
          </p>
          <p>
            Our clients include farmers, landowners, agri-enterprises, NGOs, research institutions,
            and development organisations- across the full spectrum of agricultural scale and
            ambition.
          </p>
        </div>

        <div className="research-collab-grid" aria-label="Research collaboration focus areas">
          <article>
            <span>01</span>
            <h2>Field research</h2>
            <p>Farm-level observation, soil-water review, and climate response planning.</p>
          </article>
          <article>
            <span>02</span>
            <h2>Program support</h2>
            <p>Evidence-led design for agricultural programs, pilots, and implementation partners.</p>
          </article>
          <article>
            <span>03</span>
            <h2>Climate resilience</h2>
            <p>Practical adaptation frameworks for farms facing rainfall, flood, and drought stress.</p>
          </article>
        </div>

        <Link className="research-cta" href="/contact">
          Reach out for more on research &amp; collaboration
        </Link>
      </section>
      <AgriFooter />
    </main>
  );
}
