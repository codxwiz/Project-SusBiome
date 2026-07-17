import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";

export const metadata = {
  title: "Products | SusBiome",
  description: "Upcoming SusBiome product innovation for stronger, more resilient crops.",
};

export default function ProductsPage() {
  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section className="products-section site-section subpage-section" aria-labelledby="products-title">
        <div className="section-copy section-copy--wide products-intro">
          <h1 id="products-title">Our product : Coming Soon</h1>
          <p>
            A smarter way to help crops thrive when the heat is on. A breakthrough innovation for
            stronger, more resilient plants is on the horizon.
          </p>
          <p className="products-intro__closing">Innovation is growing.</p>
        </div>
      </section>
      <AgriFooter />
    </main>
  );
}
