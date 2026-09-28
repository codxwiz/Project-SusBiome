import AgriFooter from "../../../components/AgriFooter";
import AgriPageNav from "../../../components/AgriPageNav";
import GuideReader from "../../guide/leihaao-9k4m2p/GuideReader";
import guideBlocks from "../../../lib/leihaaoGuide.json";

export const metadata = {
  title: "The Urban Farmer Project | SusBiome",
  description:
    "Leaf colour chart, feeding doses and natural plant protection for home and rooftop gardeners.",
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
};

const DOWNLOAD_PATH = "/downloads/Leihaao_Plant_Care_Guide.docx";

export default async function UrbanFarmerProjectPage({ searchParams }) {
  const params = await searchParams;
  const requestedPart = Number.parseInt(params?.part ?? "1", 10);
  const activePart = Number.isFinite(requestedPart)
    ? Math.min(3, Math.max(1, requestedPart)) - 1
    : 0;
  const title = guideBlocks.find((block) => block.type === "title");
  const subtitle = guideBlocks.find((block) => block.type === "subtitle");
  const content = guideBlocks.filter(
    (block) => !["title", "subtitle"].includes(block.type),
  );

  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <section className="leihaao-guide leihaao-guide--project">
        <section className="leihaao-intro" aria-labelledby="leihaao-title">
          <div className="leihaao-title-row">
            <h1 id="leihaao-title">{title.text}</h1>
            <a className="leihaao-download leihaao-download--title" href={DOWNLOAD_PATH} download>
              <span aria-hidden="true">↓</span>
              Download
            </a>
          </div>
          <p className="leihaao-subtitle">{subtitle.text}</p>
        </section>

        <GuideReader content={content} activePart={activePart} />
      </section>
      <AgriFooter />
    </main>
  );
}
