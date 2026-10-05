import { Suspense } from "react";
import { Dictionary } from "@/components/dictionary";
import { Skeleton } from "@/components/ui/skeleton";

export default function Home() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto w-full max-w-5xl px-4 py-10">
          <Skeleton className="mb-6 h-12 w-64" />
          <Skeleton className="h-14 w-full" />
        </main>
      }
    >
      <Dictionary />
    </Suspense>
  );
}
