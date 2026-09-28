import { redirect } from "next/navigation";

export const metadata = {
  title: "Leihaao Plant Care Guide | SusBiome",
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
};

export default async function LeihaaoGuideRedirect({ searchParams }) {
  const params = await searchParams;
  const requestedPart = Number.parseInt(params?.part ?? "1", 10);
  const part = Number.isFinite(requestedPart) ? Math.min(3, Math.max(1, requestedPart)) : 1;

  redirect(`/products/urban-farmer-project?part=${part}#guide-reader`);
}
