import type { Metadata } from "next";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Inter, Geist } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CareAuth AI",
  description: "Prior Authorization & Documentation Assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body className={`${inter.className} min-h-screen flex flex-col bg-slate-50`}>
        <TooltipProvider>
          <header className="bg-white border-b border-slate-200 py-4 px-6 sticky top-0 z-10">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <h1 className="text-xl font-bold text-slate-900">CareAuth AI</h1>
              <nav className="text-sm font-medium text-slate-600">
                <a href="/" className="mr-4 hover:text-slate-900">Dashboard</a>
                <a href="/payer" className="hover:text-slate-900">Payer Portal</a>
              </nav>
            </div>
          </header>
          <main className="flex-1 max-w-7xl w-full mx-auto p-6">
            {children}
          </main>
          <footer className="bg-white border-t border-slate-200 py-6 px-6 mt-auto">
            <div className="max-w-7xl mx-auto text-xs text-slate-500 text-center">
              CareAuth AI is an administrative decision-support tool. It does not provide medical advice and does not make coverage determinations. All policy content shown is sample data.
            </div>
          </footer>
        </TooltipProvider>
      </body>
    </html>
  );
}
