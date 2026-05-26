import { api } from "@/lib/api";
import BoothsClient from "./BoothsClient";

export const revalidate = 3600; // Enable ISR, cache page for 1 hour

const AC_ID = "GKP_URBAN";

export default async function BoothsPage() {
  let booths: Awaited<ReturnType<typeof api.booths>>["booths"] = [];
  try { booths = (await api.booths(AC_ID)).booths; } catch {}
  return <BoothsClient booths={booths} />;
}
