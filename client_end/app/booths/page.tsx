import { api } from "@/lib/api";
import BoothsClient from "./BoothsClient";

const AC_ID = "GKP_URBAN";

export default async function BoothsPage() {
  let booths: Awaited<ReturnType<typeof api.booths>>["booths"] = [];
  try { booths = (await api.booths(AC_ID)).booths; } catch {}
  return <BoothsClient booths={booths} />;
}
