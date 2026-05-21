import { api } from "@/lib/api";
import InfraClient from "./InfraClient";

const AC_ID = "GKP_URBAN";

export default async function InfrastructurePage() {
  const [overview, coverage] = await Promise.allSettled([
    api.infraOverview(),
    api.graphCoverage(AC_ID),
  ]);

  return (
    <InfraClient
      overview={overview.status === "fulfilled" ? overview.value : null}
      coverage={coverage.status === "fulfilled" ? coverage.value : null}
    />
  );
}
