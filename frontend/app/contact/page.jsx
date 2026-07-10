import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";
import ContactForm from "../../components/ContactForm";

export const metadata = {
  title: "Contact SusBiome | Agricultural Consultancy",
  description:
    "Contact SusBiome for farm assessment, research collaboration, and agricultural advisory support.",
};

export default function ContactPage() {
  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section id="contact" className="contact-section site-section subpage-section" aria-labelledby="contact-title">
        <div className="section-copy">
          <p className="story-kicker">Contact us</p>
          <h1 id="contact-title">Start with the farm, the land, or the program you want to strengthen.</h1>
          <p>
            Share the basics and SusBiome can follow up with the right next step for farm assessment,
            research collaboration, or advisory support.
          </p>
        </div>

        <ContactForm />
      </section>
      <AgriFooter />
    </main>
  );
}
