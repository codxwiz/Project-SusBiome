import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";

export const metadata = {
  title: "About SusBiome | Agricultural Consultancy",
  description:
    "SusBiome is a research-driven agricultural consultancy working at the intersection of agronomy, soil science, and climate adaptation.",
};

export default function AboutPage() {
  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section id="about" className="about-section site-section subpage-section" aria-labelledby="about-title">
        <div className="section-copy">
          <h1 id="about-title">
            Research-driven agricultural consultancy for resilient farming systems.
          </h1>
          <p>
            SusBiome is a research-driven agricultural consultancy built on one conviction: that
            farming systems can be productive, ecologically sound, and economically resilient at
            the same time. We work at the intersection of agronomy, soil science, and climate
            adaptation to design solutions that hold up in the field, not just on paper.
          </p>
        </div>

        <div className="about-visual" aria-label="SusBiome field practice">
          <div className="about-visual__image" />
          <div className="about-visual__statement">
            <span>Reach</span>
            <strong>Local practice. Global relevance.</strong>
            <p>
              Headquartered in Manipur, Northeast India - working across scales, from smallholder
              farms to institutional agricultural programs
            </p>
          </div>
        </div>

        <div className="problem-band">
          The farmers who feed the world are under compounding pressure, from rising costs,
          climate disruption, and a support system that has not kept pace. SusBiome exists to
          narrow that gap.
        </div>

        <aside className="origin-quote">
          &quot;SusBiome did not begin in a laboratory or a boardroom. It began with observation and a
          conviction that the right combination of science, planning, and partnership could help
          farming communities survive.&quot;
        </aside>
      </section>
      <AgriFooter />
    </main>
  );
}
