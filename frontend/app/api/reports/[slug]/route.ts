import { NextResponse } from "next/server";
import { getReport } from "@/lib/fetchReport";

export async function GET(
  _: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params;
    const report = await getReport(slug);
    return NextResponse.json(report, {
      headers: {
        "Cache-Control": "s-maxage=300, stale-while-revalidate=300"
      }
    });
  } catch (error) {
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 404 }
    );
  }
}
