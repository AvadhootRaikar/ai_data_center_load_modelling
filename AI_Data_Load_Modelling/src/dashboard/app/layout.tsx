import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'AI Data Center — Energy & Grid Dashboard',
  description:
    'Interactive dashboard for AI data center load modelling — electricity consumption, carbon emissions, water usage, grid analysis, and optimization scenarios using real German grid data (SMARD).',
  keywords: ['AI data center', 'energy dashboard', 'load modelling', 'carbon emissions', 'German grid', 'SMARD', 'PUE', 'optimization'],
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0a0f1a',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} bg-background`}>
      <body className="font-sans antialiased min-h-screen bg-background text-foreground">
        {children}
      </body>
    </html>
  )
}
