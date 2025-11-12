import { NextResponse } from "next/server";
import { getReport } from "@/lib/fetchReport";

interface Params {
  params: { slug: string };
}

export async function GET(_: Request, { params }: Params) {
  try {
    const report = await getReport(params.slug);
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

