import { backendFetch } from "@/lib/backendClient";
import { NextResponse } from "next/server";

interface RouteParams {
  slug: string;
}

export async function GET(
  _: Request,
  { params }: { params: Promise<RouteParams> }
) {
  const { slug } = await params;
  try {
    const response = await backendFetch(`/reports/${slug}`);
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 502 }
    );
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<RouteParams> }
) {
  const { slug } = await params;
  const body = await request.text();
  try {
    const response = await backendFetch(`/reports/${slug}/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: body || "{}"
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 502 }
    );
  }
}
