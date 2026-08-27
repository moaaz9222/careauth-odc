import { RequestDetailView } from "./RequestDetailView";

export default async function RequestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RequestDetailView requestId={id} />;
}
