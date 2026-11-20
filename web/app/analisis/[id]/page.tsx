import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Dashboard } from "@/components/analysis/Dashboard";
import { isValidId } from "@/lib/jobs";

// Enlaces privados: que no los indexen los buscadores.
export const metadata: Metadata = { title: "Tu análisis", robots: { index: false, follow: false } };

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!isValidId(id)) notFound();
  return <Dashboard id={id} />;
}
