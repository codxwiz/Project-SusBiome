import Link from "next/link";

const stats = [
  ["133", "districts monitored"],
  ["3", "hazards tracked"],
  ["4", "planning horizons"],
  ["8", "NE states"],
];

const sources = ["ERA5-Land", "NASA GPM", "CHIRPS", "SRTM", "ESA WorldCover", "IMD"];

export default function LandingPage() {
  return (
    <main className="site">
      <header className="topbar">
        <Link href="/" className="brand">
          <span className="brand-icon">S</span>
          <span>SusBiome</span>
          <small>NE-India</small>
        </Link>
        <nav className="nav-links" aria-label="Primary">
          <Link href="/console">Dashboard</Link>
          <Link href="/console#map">Risk Map</Link>
          <Link href="/console#quality">Data Quality</Link>
        </nav>
        <Link href="/console" className="nav-cta">
          Open Console
        </Link>
      </header>

      <section className="landing-hero">
        <div className="hero-copy">
          <p className="section-kicker">Climate intelligence for Northeast India</p>
          <h1>
            Understand land risk before weather becomes a field decision.
          </h1>
          <p className="hero-lede">
            SusBiome turns weather signals, satellite context, terrain, and verified
            disaster history into district-level planning outlooks for flood, drought,
            and cyclone risk.
          </p>
          <div className="hero-actions">
            <Link href="/console" className="button primary">
              View Dashboard
            </Link>
            <Link href="/console#map" className="button secondary">
              Explore Risk Map
            </Link>
          </div>
        </div>

        <div className="hero-console" aria-label="SusBiome console preview">
          <div className="console-chrome">
            <span></span>
            <span></span>
            <span></span>
            <strong>Risk Console</strong>
          </div>
          <div className="console-panel">
            <div>
              <small>Composite risk</small>
              <strong>43</strong>
              <span>Moderate</span>
            </div>
            <div>
              <small>Dominant signal</small>
              <strong>Flood</strong>
              <span>30-day outlook</span>
            </div>
          </div>
          <div className="console-map">
            <i className="map-node one"></i>
            <i className="map-node two"></i>
            <i className="map-node three"></i>
          </div>
          <div className="console-bars">
            <span style={{ height: "58%" }}></span>
            <span style={{ height: "31%" }}></span>
            <span style={{ height: "45%" }}></span>
          </div>
        </div>
      </section>

      <section className="trust-grid" aria-label="SusBiome trusted operating stats">
        {stats.map(([value, label]) => (
          <article key={label} className="trust-card">
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </section>

      <section className="product-grid">
        <article className="product-card wide">
          <p className="section-kicker">What SusBiome does</p>
          <h2>District-specific planning intelligence, not generic state summaries.</h2>
          <p>
            Users select their state and district, compare flood, drought, and cyclone
            outlook scores across 15, 30, 60, and 90 days, and inspect the physical
            land and weather signals behind the result.
          </p>
        </article>
        <article className="product-card">
          <p className="section-kicker">Data stack</p>
          <h2>Weather, land, terrain, and labels.</h2>
          <div className="source-pills">
            {sources.map((source) => (
              <span key={source}>{source}</span>
            ))}
          </div>
        </article>
        <article className="product-card">
          <p className="section-kicker">Public wording</p>
          <h2>Careful risk language.</h2>
          <p>
            The product presents a weather and physical land planning outlook. It does
            not replace official IMD alerts or local authority instructions.
          </p>
        </article>
      </section>

      <section className="ready-band">
        <p className="section-kicker">Ready</p>
        <h2>Open the district risk console.</h2>
        <p>
          Explore live district scores, map context, horizon trends, data quality,
          sources, and recommended attention notes.
        </p>
        <Link href="/console" className="button primary">
          Launch Dashboard
        </Link>
      </section>

      <footer className="footer">
        <strong>SusBiome</strong>
        <span>Flood, drought, and cyclone planning outlook for Northeast India.</span>
      </footer>
    </main>
  );
}
