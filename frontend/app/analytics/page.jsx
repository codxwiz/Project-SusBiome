import AgriFooter from "../../components/AgriFooter";
import AgriPageNav from "../../components/AgriPageNav";
import AnalyticsDashboard from "../../components/AnalyticsDashboard";

export const metadata = {
  title: "Analytics | SusBiome",
  description:
    "Climate disaster analytics for SusBiome, including hazard trends, state counts, and district-level composite risk.",
};

export default function AnalyticsPage() {
  return (
    <main className="agri-site subpage-site">
      <AgriPageNav />
      <AnalyticsDashboard />
      <AgriFooter />
    </main>
  );
}
