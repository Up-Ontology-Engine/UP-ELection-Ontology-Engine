import { api } from "@/lib/api";
import HeatMapClient from "./HeatMapClient";

export default async function HeatMapPage() {
  let coverage = null;
  try {
    coverage = await api.graphCoverage("GKP_URBAN");
  } catch {}
  return <HeatMapClient coverage={coverage} />;
}
