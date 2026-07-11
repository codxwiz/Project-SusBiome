import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";

const servicePillars = [
  {
    label: "Farm Assessment Package",
    note: "A practical first step for landowners and farmers who need a clear view of current farm risk.",
    items: [
      "Soil-water assessment",
      "Drainage review",
      "Nutrient management suggestions",
      "Basic farm redesign recommendations",
      "Climate resilience suggestions",
    ],
  },
  {
    label: "Agronomy Planning",
    note: "Field-grounded planning for crop choices, soil care, water movement, and seasonal decisions.",
    items: ["Crop system review", "Soil fertility planning", "Water-use guidance", "Seasonal risk notes"],
  },
  {
    label: "Program Evaluation",
    note: "Research and advisory support for institutions building agricultural programs that must work in real landscapes.",
    items: ["Baseline review", "Implementation support", "Outcome tracking", "Climate adaptation framing"],
  },
];

export const metadata = {
  title: "Services | SusBiome",
  description:
    "SusBiome services for farmers, landowners, agri-enterprises, NGOs, research institutions, and development organizations.",
};

export default function ServicesPage() {
  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section id="service" className="services-section site-section subpage-section" aria-labelledby="services-title">
        <div className="section-copy section-copy--wide">
          <h1 id="services-title">Field advisory for farms, landowners, and institutions.</h1>
          <p>
            We work across scales- from smallholder farms to institutional agricultural programs
            designing, implementing, and evaluating farming systems built for the realities of
            climate change and economic pressure.
          </p>
          <p>
            Our clients include farmers, landowners, agri-enterprises, NGOs, research institutions,
            and development organizations- across the full spectrum of agricultural scale and
            ambition.
          </p>
        </div>

        <div className="service-grid">
          {servicePillars.map((service, index) => (
            <article key={service.label} className="service-card">
              <div className="service-icon" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </div>
              <h2>{service.label}</h2>
              <p>{service.note}</p>
              <ul>
                {service.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        <blockquote className="commitment-quote">
          &quot;Our measure of success is not the elegance of a plan on paper, but the resilience of a
          farm system across three growing seasons, five years, and the decades that follow.&quot;
        </blockquote>

        <div className="matter-band">
          The global farming community is contracting. SusBiome exists to protect the people who
          feed the world before the pressure becomes irreversible.
        </div>
      </section>
      <AgriFooter />
    </main>
  );
}
