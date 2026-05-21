import { api } from "@/lib/api";
import HeatMapClient from "./HeatMapClient";

const AC_ID = "GKP_URBAN";

export default async function HeatMapPage() {
  let geo: Awaited<ReturnType<typeof api.geo>>["geo"] = [];
  try {
    const res = await api.geo(AC_ID);
    geo = res.geo;
  } catch {}

  return <HeatMapClient geo={geo} />;
}
