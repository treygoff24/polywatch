import { NextResponse } from "next/server";
import {
  getLiveReport,
  getReport,
  ReportFetchError
} from "@/lib/fetchReport";
import { isBackendConfigured } from "@/lib/backendClient";

export async function GET(
  _: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params;
    const report = isBackendConfigured()
      ? await getLiveReport(slug)
      : await getReport(slug);
    return NextResponse.json(report, {
      headers: {
        "Cache-Control": "s-maxage=300, stale-while-revalidate=300"
      }
    });
  } catch (error) {
    if (error instanceof ReportFetchError) {
      return NextResponse.json(
        { error: error.message },
        { status: error.status ?? 500 }
      );
    }
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 404 }
    );
  }
}
