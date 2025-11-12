import { NextResponse } from "next/server";
import { getReportIndex } from "@/lib/fetchReport";

export async function GET() {
  const index = await getReportIndex();
  return NextResponse.json(index, {
    headers: {
      "Cache-Control": "s-maxage=300, stale-while-revalidate=300"
    }
  });
}

