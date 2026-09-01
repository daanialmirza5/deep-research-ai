import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Link href="/" className="text-sm font-semibold tracking-tight">
        DeepResearch AI
      </Link>
      {children}
    </div>
  );
}
