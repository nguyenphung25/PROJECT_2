import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ParkingPro Admin Terminal',
  description: 'Parking management dashboard built with Next.js',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
