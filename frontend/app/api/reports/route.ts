import { NextResponse } from "next/server";
import { getResolvedReportIndex } from "@/lib/fetchReport";

export async function GET() {
  const { index } = await getResolvedReportIndex();
  return NextResponse.json(index, {
    headers: {
      "Cache-Control": "s-maxage=300, stale-while-revalidate=300"
    }
  });
}
