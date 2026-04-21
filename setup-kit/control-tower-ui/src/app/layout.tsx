import type { Metadata } from 'next';
import '../styles/globals.css';
import { QueryProvider } from '@/providers/QueryProvider';
import { RealtimeProvider } from '@/providers/RealtimeProvider';
import { TopNav } from '@/components/organisms/TopNav';

export const metadata: Metadata = {
  title: 'Cleya Control Tower',
  description: 'Command center for an autonomous AI company. Target: ₹41.5L MRR.',
  icons: { icon: '/favicon.svg' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg text-text antialiased">
        <QueryProvider>
          <RealtimeProvider>
            <TopNav />
            <main className="mx-auto max-w-[1440px] px-6 py-6">{children}</main>
          </RealtimeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
