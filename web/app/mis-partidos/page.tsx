import type { Metadata } from "next";

import { MyMatches } from "./MyMatches";

export const metadata: Metadata = { title: "Mis partidos", robots: { index: false } };

export default function MyMatchesPage() {
  return <MyMatches />;
}
