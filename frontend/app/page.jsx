import AgriFooter from "../components/AgriFooter";
import AgriPageNav from "../components/AgriPageNav";
import ClimateRiskPreview from "../components/ClimateRiskPreview";

const menuItems = [
  { label: "About us", href: "/about" },
  { label: "Services", href: "/services" },
  { label: "Products", href: "/products" },
  { label: "Research collaboration", href: "/research-collaboration" },
  { label: "Contact us", href: "/contact" },
];

export default function LandingPage() {
  return (
    <main className="agri-site">
      <AgriPageNav />
      <section className="agri-hero" aria-label="SusBiome agricultural consultancy">
        <div className="agri-hero__shade" />

        <div className="agri-hero__content">
          <h1>SusBiome</h1>
          <p className="agri-motto">
            Science for the soil. Solutions for the farmer. Resilience for the future.
          </p>
        </div>

        <div className="agri-hero__footer">
          <p className="agri-descriptor">
            Agricultural consultancy · Agronomy &amp; Sustainability Research
          </p>
          <nav className="agri-menu" aria-label="Primary">
            {menuItems.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      </section>

      <section className="field-film" aria-label="Farmer working in paddy field placeholder video">
        <div className="field-film__frame">
          <div className="field-film__motion" />
          <div className="field-film__caption">
            <span>8 sec placeholder film</span>
            <strong>Farmer working on a paddy field</strong>
          </div>
        </div>
      </section>

      <section className="climate-story" aria-labelledby="climate-crisis-title">
        <h2 id="climate-crisis-title">
          Farming decisions are now being made in a climate that no longer behaves like the past.
        </h2>
        <p>
          Rain arrives late, dry spells stretch longer, floods rise faster, and storms can undo a season of
          work in a few hours. For farmers and landowners, climate risk is no longer an abstract future
          problem. It is becoming a local, practical question: what is changing around my land, and how
          exposed could I be?
        </p>
      </section>

      <section className="risk-awareness" aria-labelledby="risk-awareness-title">
        <div className="risk-awareness__hook">
          <p className="story-kicker">District readiness</p>
          <h2>Is Your District Ready for Tomorrow&apos;s Climate?</h2>
          <p className="risk-awareness__question">
            What if you could understand your district&apos;s climate vulnerability before making critical
            agricultural decisions?
          </p>
          <p>
            Our interactive tool estimates the probability of climate vulnerability for districts across
            Northeast India, helping you identify areas that may require greater adaptation and resilience
            planning.
          </p>
          <p className="risk-awareness__start">Start exploring in less than a minute.</p>
        </div>

        <div className="risk-awareness__intro">
          <h2 id="risk-awareness-title">Know Your Climate Risk</h2>
          <p>
            A simple educational risk-preview experience to help visitors recognize vulnerability, build
            trust in SusBiome, and take the first step toward a deeper consultation.
          </p>
        </div>
        <ClimateRiskPreview />
      </section>

      <AgriFooter />
    </main>
  );
}
