import type { Metadata } from "next";

import { UploadWizard } from "@/components/upload/UploadWizard";

export const metadata: Metadata = { title: "Analizar mi partido" };

export default function UploadPage() {
  return <UploadWizard />;
}
